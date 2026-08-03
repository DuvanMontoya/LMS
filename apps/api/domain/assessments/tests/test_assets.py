from __future__ import annotations

from django.db import DatabaseError, transaction
from django.test import TestCase

from domain.assets.choices import AssetKind, AssetVersionStatus
from domain.assets.models import Asset, AssetVersion

from ..choices import AuthoringStatus
from ..exceptions import AssessmentInvalid
from ..models import AssessmentAssetReference
from ..services import create_question, transition_question_revision
from .support import AssessmentFixtureMixin, cloned_definition


class AssessmentAssetReferenceTests(AssessmentFixtureMixin, TestCase):
    def _asset_version(self, context: dict[str, object], *, kind: str = "image"):
        owner = context["owner"]
        asset = Asset.objects.create(
            organization=context["organization"],
            kind=kind,
            name="Gráfica evaluativa",
            created_by=owner,
            updated_by=owner,
        )
        return AssetVersion.objects.create(
            asset=asset,
            number=1,
            status=AssetVersionStatus.READY,
            original_filename="grafica.png",
            declared_mime_type="image/png",
            detected_mime_type="image/png",
            extension=".png",
            size_bytes=128,
            sha256="a" * 64,
            storage_bucket="academic-assets",
            storage_key=f"ready/{asset.id}/grafica.png",
            expected_asset_lock_version=1,
            created_by=owner,
        )

    def test_approval_pins_prompt_and_choice_asset_versions(self) -> None:
        context = self.assessment_context()
        version = self._asset_version(context)
        definition = cloned_definition("single_choice")
        definition["public"]["prompt"]["content"].append(  # type: ignore[index]
            {
                "type": "imageAsset",
                "attrs": {
                    "nodeId": "50000000-0000-4000-8000-000000000002",
                    "assetVersionId": str(version.id),
                    "altText": "Plano cartesiano con una parábola.",
                    "caption": "Figura 1",
                    "decorative": False,
                    "displaySize": "large",
                },
            }
        )
        definition["public"]["options"][0]["media"] = {  # type: ignore[index]
            "asset_version_id": str(version.id),
            "kind": "image",
            "alt_text": "Parábola abierta hacia arriba.",
        }
        _, revision = create_question(
            actor=context["owner"],
            bank=context["bank"],
            code="ALG-Q-MEDIA",
            question_type="single_choice",
            definition=definition,
        )
        revision, _ = transition_question_revision(
            actor=context["owner"],
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.IN_REVIEW,
        )
        _, question_version = transition_question_revision(
            actor=context["question_revision"].status_changed_by,
            revision=revision,
            expected_version=revision.lock_version,
            to_status=AuthoringStatus.APPROVED,
        )
        assert question_version is not None
        references = AssessmentAssetReference.objects.filter(
            question_version=question_version
        ).order_by("location")
        self.assertEqual(references.count(), 2)
        self.assertEqual(
            {reference.reference_role for reference in references},
            {"primary", "choice"},
        )
        self.assertEqual(
            question_version.public["options"][0]["media"]["asset_version_id"],
            str(version.id),
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                references.update(location="definition.public.options.99.media")

    def test_question_rejects_wrong_asset_kind_before_persisting(self) -> None:
        context = self.assessment_context()
        version = self._asset_version(context, kind=AssetKind.DOCUMENT)
        definition = cloned_definition("single_choice")
        definition["public"]["options"][0]["media"] = {  # type: ignore[index]
            "asset_version_id": str(version.id),
            "kind": "image",
            "alt_text": "No debe aceptarse.",
        }
        with self.assertRaises(AssessmentInvalid):
            create_question(
                actor=context["owner"],
                bank=context["bank"],
                code="ALG-Q-WRONG-ASSET",
                question_type="single_choice",
                definition=definition,
            )
