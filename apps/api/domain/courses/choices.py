from django.db import models


class CourseStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    ARCHIVED = "archived", "Archivado"


class AuthoringStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    IN_REVIEW = "in_review", "En revisión"
    CHANGES_REQUESTED = "changes_requested", "Cambios solicitados"
    APPROVED = "approved", "Aprobada"


EDITABLE_AUTHORING_STATUSES = frozenset(
    {AuthoringStatus.DRAFT, AuthoringStatus.CHANGES_REQUESTED}
)
OPEN_AUTHORING_STATUSES = frozenset(
    {
        AuthoringStatus.DRAFT,
        AuthoringStatus.IN_REVIEW,
        AuthoringStatus.CHANGES_REQUESTED,
    }
)


class StructureStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    ARCHIVED = "archived", "Archivado"


class SubjectAlignmentType(models.TextChoices):
    PRIMARY = "primary", "Principal"
    SUPPORTING = "supporting", "Complementaria"
