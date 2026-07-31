# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any, cast

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .canonical import canonical_json_bytes, deep_json_copy
from .choices import (
    AttemptStatus,
    GradeSource,
    GradingRevisionSource,
    GradingStatus,
    ResponseStatus,
)
from .exceptions import AssessmentConflict, AssessmentInvalid
from .math.equivalence import MathEquivalenceOutcome, evaluate_equivalence
from .models import (
    AssessmentGradingPolicy,
    AssessmentGradingRevision,
    AssessmentVersion,
    Attempt,
    AttemptGradeVersion,
    AttemptItemGradeVersion,
    ManualGradeDecision,
    Response,
)
from .schemas import validate_grading_revision_snapshot, validate_scoring_policy
from .scoring import (
    LEGACY_SCORING_POLICIES,
    SCORING_ENGINE_VERSION,
    basis_points,
    quantize_score,
    score_question,
)


def _actor_id(actor: object | None) -> object | None:
    return getattr(actor, "pk", None)


def _public_items(version: AssessmentVersion) -> dict[str, dict[str, Any]]:
    items = {
        str(item["id"]): item
        for section in version.public_snapshot["sections"]
        for item in section["items"]
    }
    for pool in version.public_snapshot.get("pools", []):
        for candidate in pool["candidates"]:
            items[str(candidate["id"])] = {
                **candidate,
                "points": pool["points_per_item"],
            }
    return items


def original_grading_snapshot(version: AssessmentVersion) -> dict[str, Any]:
    public_items = _public_items(version)
    items: list[dict[str, Any]] = []
    for entry in version.grading_snapshot["items"]:
        source_id = str(entry["assessment_item_id"])
        public_item = public_items[source_id]
        question_type = str(entry["type"])
        grading_payload = deep_json_copy(entry["grading"])
        if question_type == "multiple_choice":
            grading_payload["option_ids"] = [
                option["id"] for option in public_item["question"]["options"]
            ]
        if question_type == "mathematical_expression":
            grading_payload["maximum_latex_length"] = public_item["question"][
                "maximum_latex_length"
            ]
        policy = {
            "source_kind": ("pool_candidate" if entry.get("pool_id") else "fixed_item"),
            "source_id": source_id,
            "question_version_id": str(entry["question_version_id"]),
            "question_type": question_type,
            "scoring_policy": LEGACY_SCORING_POLICIES.get(
                question_type,
                str(grading_payload.get("equivalence_strategy", "")),
            ),
            "grading_payload": grading_payload,
            "maximum_score": str(public_item["points"]),
            "feedback_payload": deep_json_copy(entry["feedback"]),
            "scoring_engine_version": SCORING_ENGINE_VERSION,
        }
        validate_scoring_policy(
            {
                key: value
                for key, value in policy.items()
                if key not in {"source_kind", "source_id", "question_version_id"}
            }
        )
        items.append(policy)
    snapshot = {
        "schema_version": 1,
        "scoring_engine_version": SCORING_ENGINE_VERSION,
        "items": items,
    }
    return validate_grading_revision_snapshot(snapshot)


@transaction.atomic
def create_original_grading_policy(
    *,
    version: AssessmentVersion,
    actor: object | None,
) -> AssessmentGradingPolicy:
    existing = AssessmentGradingPolicy.objects.select_for_update(of=("self",)).filter(
        assessment_version=version
    )
    if existing.exists():
        return existing.select_related("current_revision").get()
    policy = AssessmentGradingPolicy.objects.create(assessment_version=version)
    snapshot = original_grading_snapshot(version)
    revision = AssessmentGradingRevision.objects.create(
        policy=policy,
        number=1,
        source=GradingRevisionSource.ORIGINAL,
        reason="",
        grading_snapshot=snapshot,
        snapshot_digest=hashlib.sha256(canonical_json_bytes(snapshot)).hexdigest(),
        created_by_id=_actor_id(actor),
    )
    policy.current_revision = revision
    policy.save(update_fields=["current_revision", "updated_at"])
    return policy


@transaction.atomic
def create_scoring_correction(
    *,
    actor: object,
    assessment_version: AssessmentVersion,
    expected_policy_version: int,
    reason: str,
    item_overrides: dict[str, dict[str, object]],
) -> AssessmentGradingRevision:
    policy = (
        AssessmentGradingPolicy.objects.select_for_update(of=("self",))
        .select_related("current_revision")
        .get(assessment_version=assessment_version)
    )
    if policy.lock_version != expected_policy_version:
        raise AssessmentConflict("La policy de scoring cambió durante la edición.")
    if not reason.strip():
        raise AssessmentInvalid("La corrección exige una razón.")
    current = policy.current_revision
    if current is None:
        raise AssessmentConflict("La policy no tiene una revisión vigente.")
    snapshot = deep_json_copy(current.grading_snapshot)
    items_by_id = {str(item["source_id"]): item for item in snapshot["items"]}
    if not item_overrides or not set(item_overrides).issubset(items_by_id):
        raise AssessmentInvalid("La corrección referencia items inexistentes.")
    for source_id, override in item_overrides.items():
        if set(override) - {"scoring_policy", "grading_payload"}:
            raise AssessmentInvalid(
                "La corrección sólo admite policy y grading payload."
            )
        item = items_by_id[source_id]
        candidate = {
            **item,
            **deep_json_copy(override),
        }
        validate_scoring_policy(
            {
                key: value
                for key, value in candidate.items()
                if key not in {"source_kind", "source_id", "question_version_id"}
            }
        )
        item.update(deep_json_copy(override))
    snapshot = validate_grading_revision_snapshot(snapshot)
    revision = AssessmentGradingRevision.objects.create(
        policy=policy,
        number=current.number + 1,
        previous_revision=current,
        source=GradingRevisionSource.CORRECTION,
        reason=reason.strip(),
        grading_snapshot=snapshot,
        snapshot_digest=hashlib.sha256(canonical_json_bytes(snapshot)).hexdigest(),
        created_by_id=_actor_id(actor),
    )
    policy.current_revision = revision
    policy.lock_version += 1
    policy.save(update_fields=["current_revision", "lock_version", "updated_at"])
    return revision


def _manual_decisions(attempt: Attempt) -> dict[object, ManualGradeDecision]:
    decisions: dict[object, ManualGradeDecision] = {}
    queryset = (
        ManualGradeDecision.objects.filter(response__attempt_item__attempt=attempt)
        .select_related("response")
        .order_by("response_id", "-sequence")
    )
    for decision in queryset:
        decisions.setdefault(decision.response_id, decision)
    return decisions


def evaluate_symbolic_responses(
    *,
    attempt: Attempt,
    grading_revision: AssessmentGradingRevision,
) -> dict[str, MathEquivalenceOutcome]:
    policies = {
        str(item["source_id"]): item
        for item in grading_revision.grading_snapshot["items"]
    }
    responses = {
        response.attempt_item_id: response
        for response in Response.objects.filter(attempt_item__attempt=attempt)
    }
    outcomes: dict[str, MathEquivalenceOutcome] = {}
    for item in attempt.items.order_by("display_position"):
        policy = policies[str(item.assessment_item_id)]
        if (
            policy["question_type"] != "mathematical_expression"
            or policy["scoring_policy"] != "symbolic_common_domain"
        ):
            continue
        response = responses.get(item.id)
        value = response.response.get("value") if response is not None else None
        if not isinstance(value, dict) or "mathjson" not in value:
            continue
        grading = policy["grading_payload"]
        outcomes[str(item.id)] = evaluate_equivalence(
            expected_mathjson=grading["expected_mathjson"],
            submitted_mathjson=value["mathjson"],
            allowed_symbols=grading["allowed_symbols"],
            allowed_functions=grading["allowed_functions"],
            symbol_assumptions=grading["symbol_assumptions"],
        )
    return outcomes


@transaction.atomic
def create_attempt_grade(
    *,
    attempt: Attempt,
    grading_revision: AssessmentGradingRevision,
    source: str,
    actor: object | None,
    symbolic_outcomes: dict[str, MathEquivalenceOutcome] | None = None,
) -> AttemptGradeVersion:
    locked = (
        Attempt.objects.select_for_update(of=("self",))
        .select_related("assessment_version")
        .get(pk=attempt.pk)
    )
    if locked.submitted_at is None:
        raise AssessmentConflict("El intento aún no fue enviado.")
    if grading_revision.policy.assessment_version_id != locked.assessment_version_id:
        raise AssessmentInvalid("La revisión de scoring pertenece a otra evaluación.")
    if source in {GradeSource.INITIAL, GradeSource.REGRADE}:
        existing = AttemptGradeVersion.objects.filter(
            attempt=locked,
            grading_revision=grading_revision,
            source__in=[GradeSource.INITIAL, GradeSource.REGRADE],
        ).first()
        if existing is not None:
            return existing

    policy_items = {
        str(item["source_id"]): item
        for item in grading_revision.grading_snapshot["items"]
    }
    attempt_items = list(
        locked.items.select_related("response", "question_version").order_by(
            "display_position"
        )
    )
    responses = {
        response.attempt_item_id: response
        for response in Response.objects.select_for_update().filter(
            attempt_item__attempt=locked
        )
    }
    manual_decisions = _manual_decisions(locked)
    now = timezone.now()
    automatic_score = Decimal("0.000")
    manual_score = Decimal("0.000")
    item_rows: list[dict[str, object]] = []
    pending_manual = False
    for item in attempt_items:
        policy_item = policy_items.get(str(item.assessment_item_id))
        if policy_item is None:
            raise AssessmentInvalid("La revision de scoring no cubre el intento.")
        response = responses.get(item.id)
        if response is None:
            response = Response.objects.create(
                attempt_item=item,
                response={
                    "schema_version": 1,
                    "type": item.public_snapshot["type"],
                    "value": None,
                },
                status=ResponseStatus.UNANSWERED,
                saved_at=now,
            )
            responses[item.id] = response
        outcome = (symbolic_outcomes or {}).get(str(item.id))
        result = score_question(
            question_type=policy_item["question_type"],
            scoring_policy=policy_item["scoring_policy"],
            grading=policy_item["grading_payload"],
            response=response.response,
            maximum=Decimal(policy_item["maximum_score"]),
            symbolic_outcome=outcome,
        )
        manual = manual_decisions.get(response.id)
        if manual is not None:
            item_score = quantize_score(manual.score)
            credit = basis_points(score=item_score, maximum=item.points)
            item_status = GradingStatus.GRADED
            is_correct = credit == 10000
            reason = ""
            feedback_key = "manual"
            manual_score += item_score
            response.status = ResponseStatus.MANUALLY_GRADED
        elif result.requires_manual:
            item_score = Decimal("0.000")
            credit = 0
            item_status = GradingStatus.PENDING_MANUAL
            is_correct = None
            reason = result.manual_review_reason
            feedback_key = result.feedback_key
            pending_manual = True
            response.status = ResponseStatus.PENDING_MANUAL
        else:
            item_score = result.score
            credit = result.credit_basis_points
            item_status = GradingStatus.GRADED
            is_correct = result.is_correct
            reason = ""
            feedback_key = result.feedback_key
            automatic_score += item_score
            response.status = ResponseStatus.AUTO_GRADED
        response.score = item_score
        response.graded_at = now
        response.grading_version += 1
        response.save(
            update_fields=[
                "score",
                "status",
                "graded_at",
                "grading_version",
                "updated_at",
            ]
        )
        item_rows.append(
            {
                "attempt_item": item,
                "response": response,
                "credit_basis_points": credit,
                "score": item_score,
                "maximum_score": item.points,
                "grading_status": item_status,
                "is_correct": is_correct,
                "feedback_key": feedback_key,
                "manual_review_reason": reason,
            }
        )
    automatic_score = quantize_score(automatic_score)
    manual_score = quantize_score(manual_score)
    final_score = quantize_score(automatic_score + manual_score)
    percent = (
        None
        if pending_manual
        else basis_points(score=final_score, maximum=locked.maximum_score)
    )
    grade_status = (
        GradingStatus.PENDING_MANUAL if pending_manual else GradingStatus.GRADED
    )
    number = (
        AttemptGradeVersion.objects.select_for_update()
        .filter(attempt=locked)
        .aggregate(maximum=Max("number"))["maximum"]
        or 0
    ) + 1
    digest_payload = {
        "attempt_id": str(locked.id),
        "number": number,
        "previous_grade_id": (
            str(locked.current_grade_id) if locked.current_grade_id else None
        ),
        "grading_revision_id": str(grading_revision.id),
        "source": source,
        "scoring_engine_version": SCORING_ENGINE_VERSION,
        "automatic_score": format(automatic_score, "f"),
        "manual_score": format(manual_score, "f"),
        "final_score": format(final_score, "f"),
        "maximum_score": format(locked.maximum_score, "f"),
        "percent_basis_points": percent,
        "grading_status": grade_status,
        "items": [
            {
                "attempt_item_id": str(row["attempt_item"].id),
                "credit_basis_points": row["credit_basis_points"],
                "score": format(cast(Decimal, row["score"]), "f"),
                "grading_status": row["grading_status"],
            }
            for row in item_rows
        ],
    }
    grade = AttemptGradeVersion.objects.create(
        attempt=locked,
        number=number,
        previous_grade=locked.current_grade,
        grading_revision=grading_revision,
        source=source,
        scoring_engine_version=SCORING_ENGINE_VERSION,
        automatic_score=automatic_score,
        manual_score=manual_score,
        final_score=final_score,
        maximum_score=locked.maximum_score,
        percent_basis_points=percent,
        passed=(
            None
            if percent is None
            else percent >= locked.assessment_version.pass_basis_points
        ),
        grading_status=grade_status,
        digest=hashlib.sha256(canonical_json_bytes(digest_payload)).hexdigest(),
        created_by_id=_actor_id(actor),
    )
    AttemptItemGradeVersion.objects.bulk_create(
        [AttemptItemGradeVersion(attempt_grade=grade, **row) for row in item_rows]
    )
    locked.current_grade = grade
    locked.auto_score = automatic_score
    locked.manual_score = manual_score
    locked.total_score = final_score
    locked.basis_points = percent
    locked.passed = grade.passed
    locked.status = (
        AttemptStatus.PENDING_MANUAL if pending_manual else AttemptStatus.GRADED
    )
    locked.graded_at = None if pending_manual else now
    locked.lock_version += 1
    locked.save(
        update_fields=[
            "current_grade",
            "auto_score",
            "manual_score",
            "total_score",
            "basis_points",
            "passed",
            "status",
            "graded_at",
            "lock_version",
            "updated_at",
        ]
    )
    from .gradebooks import refresh_gradebook_for_attempt

    refresh_gradebook_for_attempt(attempt=locked)
    return grade
