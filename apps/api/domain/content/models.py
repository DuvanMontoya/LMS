# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from domain.assets.models import AssetVersion
from domain.courses.models import CourseUnit

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


class UnitContentDocument(models.Model):
    if TYPE_CHECKING:
        versions: RelatedManager[UnitContentVersion]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(
        CourseUnit,
        on_delete=models.PROTECT,
        related_name="content_document",
    )
    current_version = models.OneToOneField(
        "UnitContentVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        editable=False,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="unit_content_documents_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="unit_content_documents_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["updated_at"], name="content_document_updated_ix")
        ]

    def __str__(self) -> str:
        return f"{self.unit}:content"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("El documento se preserva; no se elimina físicamente.")


class UnitContentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        UnitContentDocument,
        on_delete=models.PROTECT,
        related_name="versions",
    )
    number = models.PositiveIntegerField(editable=False)
    schema_version = models.PositiveIntegerField(editable=False)
    content = models.JSONField(editable=False)
    plain_text = models.TextField(editable=False)
    character_count = models.PositiveIntegerField(editable=False)
    word_count = models.PositiveIntegerField(editable=False)
    node_count = models.PositiveIntegerField(editable=False)
    digest = models.CharField(max_length=64, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="unit_content_versions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "number"],
                name="content_version_document_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0),
                name="content_version_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(schema_version__gt=0),
                name="content_version_schema_positive",
            ),
            models.CheckConstraint(
                condition=Q(character_count__gte=0),
                name="content_version_chars_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(word_count__gte=0),
                name="content_version_words_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(node_count__gte=0),
                name="content_version_nodes_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(digest__regex=r"^[0-9a-f]{64}$"),
                name="content_version_digest_sha256",
            ),
        ]
        indexes = [
            models.Index(
                fields=["document", "created_at"],
                name="content_ver_doc_created_ix",
            ),
            models.Index(fields=["digest"], name="content_version_digest_ix"),
            models.Index(
                fields=["created_by", "created_at"],
                name="content_ver_actor_created_ix",
            ),
        ]
        ordering = ("-number",)

    def __str__(self) -> str:
        return f"{self.document}:v{self.number}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Las versiones de contenido son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Las versiones de contenido no se eliminan.")


class UnitLessonResource(models.Model):
    """One release-pinned private asset for a non-document lesson.

    This is mutable only while its owning course revision is editable.  A
    publication copies its immutable AssetVersion identifier into the release
    snapshot; it never carries an object key or a signed URL.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.OneToOneField(
        CourseUnit,
        on_delete=models.PROTECT,
        related_name="lesson_resource",
    )
    asset_version = models.ForeignKey(
        AssetVersion,
        on_delete=models.PROTECT,
        related_name="lesson_resource_bindings",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lesson_resources_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="lesson_resources_updated",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["asset_version"], name="content_lesson_res_asset_ix")
        ]

    def __str__(self) -> str:
        return f"{self.unit_id}:{self.asset_version_id}"


class ContentAssetReference(models.Model):
    class ReferenceRole(models.TextChoices):
        PRIMARY = "primary", "Primary"
        CAPTIONS = "captions", "Captions"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_version = models.ForeignKey(
        UnitContentVersion,
        on_delete=models.PROTECT,
        related_name="asset_references",
    )
    node_id = models.UUIDField(editable=False)
    asset_version = models.ForeignKey(
        AssetVersion,
        on_delete=models.PROTECT,
        related_name="content_references",
    )
    reference_role = models.CharField(
        max_length=16, choices=ReferenceRole.choices, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["content_version", "node_id", "reference_role"],
                name="content_asset_ref_node_role_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=["content_version"], name="content_asset_ref_version_ix"
            ),
            models.Index(fields=["asset_version"], name="content_asset_ref_asset_ix"),
            models.Index(fields=["node_id"], name="content_asset_ref_node_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.content_version_id}:{self.node_id}:{self.reference_role}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Las referencias de assets son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Las referencias de assets no se eliminan.")
