# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from domain.courses.models import Course, CourseRevision

from .choices import PublicationEventType, PublicationStatus


class CoursePublication(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.OneToOneField(
        Course, on_delete=models.PROTECT, related_name="publication"
    )
    current_release = models.ForeignKey(
        "CourseRelease",
        on_delete=models.PROTECT,
        related_name="current_for_publications",
        editable=False,
    )
    status = models.CharField(
        max_length=10,
        choices=PublicationStatus.choices,
        default=PublicationStatus.ACTIVE,
        editable=False,
    )
    lock_version = models.PositiveIntegerField(default=1, editable=False)
    first_published_at = models.DateTimeField()
    first_published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_publications_first_published",
    )
    last_published_at = models.DateTimeField()
    last_published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_publications_last_published",
    )
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="course_publications_withdrawn",
    )
    withdrawal_note = models.TextField(max_length=2_000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(lock_version__gt=0),
                name="publishing_publication_lock_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=PublicationStatus.ACTIVE,
                        withdrawn_at__isnull=True,
                        withdrawn_by__isnull=True,
                        withdrawal_note="",
                    )
                    | (
                        Q(
                            status=PublicationStatus.WITHDRAWN,
                            withdrawn_at__isnull=False,
                            withdrawn_by__isnull=False,
                        )
                        & ~Q(withdrawal_note="")
                    )
                ),
                name="publishing_publication_lifecycle",
            ),
        ]
        indexes = [
            models.Index(fields=["status"], name="publishing_pub_status_ix"),
            models.Index(fields=["current_release"], name="publishing_pub_current_ix"),
        ]

    def __str__(self) -> str:
        return f"{self.course}:release-{self.current_release.number}"

    def clean(self) -> None:
        super().clean()
        self.withdrawal_note = self.withdrawal_note.strip()
        if self.current_release_id and self.current_release.course_id != self.course_id:
            raise ValidationError(
                {"current_release": "El release actual pertenece a otro curso."}
            )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("La publicación se retira; no se elimina físicamente.")


class CourseRelease(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="releases"
    )
    number = models.PositiveIntegerField(editable=False)
    source_revision = models.OneToOneField(
        CourseRevision, on_delete=models.PROTECT, related_name="release"
    )
    previous_release = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="next_releases",
        editable=False,
    )
    schema_version = models.PositiveIntegerField(editable=False)
    snapshot = models.JSONField(editable=False)
    snapshot_digest = models.CharField(max_length=64, editable=False)
    snapshot_size_bytes = models.PositiveIntegerField(editable=False)
    title = models.CharField(max_length=200, editable=False)
    summary = models.TextField(max_length=1_200, editable=False)
    language_code = models.CharField(max_length=12, editable=False)
    estimated_duration_minutes = models.PositiveIntegerField(
        null=True, blank=True, editable=False
    )
    module_count = models.PositiveIntegerField(editable=False)
    unit_count = models.PositiveIntegerField(editable=False)
    word_count = models.PositiveIntegerField(editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_releases_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "number"],
                name="publishing_release_course_number_unique",
            ),
            models.CheckConstraint(
                condition=Q(number__gt=0),
                name="publishing_release_number_positive",
            ),
            models.CheckConstraint(
                condition=Q(schema_version__gt=0),
                name="publishing_release_schema_positive",
            ),
            models.CheckConstraint(
                condition=Q(snapshot_size_bytes__gt=0),
                name="publishing_release_size_positive",
            ),
            models.CheckConstraint(
                condition=Q(snapshot_digest__regex=r"^[0-9a-f]{64}$"),
                name="publishing_release_digest_sha256",
            ),
            models.CheckConstraint(
                condition=Q(estimated_duration_minutes__isnull=True)
                | Q(estimated_duration_minutes__gt=0),
                name="publishing_release_duration_positive",
            ),
            models.CheckConstraint(
                condition=Q(previous_release__isnull=True)
                | ~Q(previous_release=F("id")),
                name="publishing_release_not_self_previous",
            ),
        ]
        indexes = [
            models.Index(
                fields=["course", "created_at"], name="pub_rel_course_created_ix"
            ),
            models.Index(fields=["snapshot_digest"], name="publishing_rel_digest_ix"),
        ]
        ordering = ("number",)

    def __str__(self) -> str:
        return f"{self.course}:release-{self.number}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Los releases son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Los releases no se eliminan.")

    def clean(self) -> None:
        super().clean()
        if self.source_revision_id:
            if self.source_revision.course_id != self.course_id:
                raise ValidationError(
                    {"source_revision": "La revisión pertenece a otro curso."}
                )
        if self.previous_release_id:
            if (
                self.previous_release.course_id != self.course_id
                or self.previous_release.number != self.number - 1
            ):
                raise ValidationError(
                    {"previous_release": "El release anterior no es contiguo."}
                )
        elif self.number != 1:
            raise ValidationError(
                {"previous_release": "Sólo el release 1 puede no tener anterior."}
            )


class CoursePublicationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT, related_name="publication_events"
    )
    publication = models.ForeignKey(
        CoursePublication, on_delete=models.PROTECT, related_name="events"
    )
    release = models.ForeignKey(
        CourseRelease,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="events",
    )
    revision = models.ForeignKey(
        CourseRevision,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="publication_events",
    )
    event_type = models.CharField(max_length=32, choices=PublicationEventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="course_publication_events",
    )
    note = models.TextField(max_length=2_000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        event_type=PublicationEventType.RELEASE_PUBLISHED,
                        release__isnull=False,
                    )
                    | (
                        Q(
                            event_type=PublicationEventType.PUBLICATION_WITHDRAWN,
                            release__isnull=False,
                        )
                        & ~Q(note="")
                    )
                    | Q(
                        event_type=PublicationEventType.DRAFT_CREATED_FROM_RELEASE,
                        release__isnull=False,
                        revision__isnull=False,
                    )
                ),
                name="publishing_event_payload",
            )
        ]
        indexes = [
            models.Index(
                fields=["course", "created_at"], name="pub_evt_course_created_ix"
            ),
            models.Index(
                fields=["publication", "created_at"],
                name="publishing_evt_pub_created_ix",
            ),
            models.Index(
                fields=["release", "created_at"], name="publishing_evt_rel_created_ix"
            ),
        ]
        ordering = ("created_at", "id")

    def __str__(self) -> str:
        return f"{self.course}:{self.event_type}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise ValidationError("Los eventos de publicación son inmutables.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("Los eventos de publicación no se eliminan.")

    def clean(self) -> None:
        super().clean()
        self.note = self.note.strip()
        if self.publication.course_id != self.course_id:
            raise ValidationError(
                {"publication": "La publicación pertenece a otro curso."}
            )
        if self.release_id and self.release.course_id != self.course_id:
            raise ValidationError({"release": "El release pertenece a otro curso."})
        if self.revision_id and self.revision.course_id != self.course_id:
            raise ValidationError({"revision": "La revisión pertenece a otro curso."})
