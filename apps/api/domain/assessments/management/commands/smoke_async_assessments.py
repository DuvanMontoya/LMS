# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from domain.assessments.choices import AttemptStatus, JobStatus
from domain.assessments.management.commands.bootstrap_demo_assessments import (
    DEMO_ASSESSMENT,
    DEMO_ORGANIZATION,
)
from domain.assessments.models import AssessmentDelivery, Attempt, AttemptGradingJob
from domain.assessments.services import save_response, start_attempt, submit_attempt
from domain.organizations.models import Organization


class Command(BaseCommand):
    help = "Envía una expresión demo y verifica una tarea real del worker Linux."

    def handle(self, *args: object, **options: object) -> None:
        if not settings.DEBUG:
            raise CommandError("El smoke asíncrono sólo se permite con DEBUG=True.")
        organization = Organization.objects.filter(slug=DEMO_ORGANIZATION).first()
        if organization is None:
            raise CommandError("Ejecuta primero pnpm assessments:demo.")
        delivery = (
            AssessmentDelivery.objects.filter(
                organization=organization,
                assessment_version__assessment__slug=DEMO_ASSESSMENT,
                name="Diagnóstico avanzado demo activo",
            )
            .select_related("assessment_version__grading_policy__current_revision")
            .order_by("-created_at")
            .first()
        )
        if delivery is None:
            raise CommandError("No existe la entrega avanzada demo.")
        assignment = (
            delivery.assignments.filter(status="active")
            .select_related("release_assignment__enrollment__membership__user")
            .first()
        )
        if assignment is None:
            raise CommandError("La entrega demo no tiene learner asignado.")
        learner = assignment.release_assignment.enrollment.membership.user
        completed = (
            Attempt.objects.filter(
                delivery_assignment=assignment,
                assessment_version=delivery.assessment_version,
                current_grade__grading_revision=(
                    delivery.assessment_version.grading_policy.current_revision
                ),
            )
            .exclude(status=AttemptStatus.IN_PROGRESS)
            .order_by("-attempt_number")
            .first()
        )
        if completed is not None:
            job = completed.grading_job
            if job.attempts < 1 or job.status not in {
                JobStatus.COMPLETED,
                JobStatus.COMPLETED_WITH_ERRORS,
            }:
                raise CommandError(
                    "El intento existe, pero no prueba ejecución del worker."
                )
            self._success(completed, job)
            return

        attempt = start_attempt(actor=learner, assignment=assignment)
        math_item = next(
            (
                item
                for item in attempt.items.order_by("display_position")
                if item.public_snapshot["type"] == "mathematical_expression"
            ),
            None,
        )
        if math_item is None:
            raise CommandError("El intento demo no materializó la pregunta matemática.")
        attempt, _ = save_response(
            actor=learner,
            attempt=attempt,
            attempt_item=math_item,
            expected_version=attempt.lock_version,
            payload={
                "schema_version": 1,
                "type": "mathematical_expression",
                "value": {
                    "latex": "1+x",
                    "mathjson": ["Add", 1, "x"],
                },
            },
        )
        attempt = submit_attempt(
            actor=learner,
            attempt=attempt,
            expected_version=attempt.lock_version,
        )
        if attempt.status != AttemptStatus.GRADING_PENDING:
            raise CommandError("El submit matemático no quedó grading_pending.")
        job = AttemptGradingJob.objects.get(attempt=attempt)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            job.refresh_from_db()
            attempt.refresh_from_db()
            if job.status in {
                JobStatus.COMPLETED,
                JobStatus.COMPLETED_WITH_ERRORS,
                JobStatus.FAILED,
            }:
                break
            time.sleep(0.5)
        if job.status not in {JobStatus.COMPLETED, JobStatus.COMPLETED_WITH_ERRORS}:
            raise CommandError(
                f"El worker no completó el job; status={job.status}; "
                f"error={job.last_error_code or 'none'}."
            )
        if attempt.current_grade_id is None or job.attempts < 1:
            raise CommandError("El worker no materializó una grade version.")
        math_grade = attempt.current_grade.item_grades.get(attempt_item=math_item)
        if math_grade.credit_basis_points != 10_000:
            raise CommandError("La expresión equivalente no obtuvo crédito completo.")
        self._success(attempt, job)

    def _success(self, attempt: Attempt, job: AttemptGradingJob) -> None:
        self.stdout.write(
            self.style.SUCCESS(
                "Async assessment smoke PASS: "
                f"attempt={attempt.id}; job={job.id}; "
                f"worker_attempts={job.attempts}; status={job.status}."
            )
        )
