from django.db import models


class CohortStatus(models.TextChoices):
    ACTIVE = "active", "Activa"
    ARCHIVED = "archived", "Archivada"


class EnrollmentStatus(models.TextChoices):
    ACTIVE = "active", "Activa"
    SUSPENDED = "suspended", "Suspendida"
    REVOKED = "revoked", "Revocada"


class AssignmentReason(models.TextChoices):
    INITIAL = "initial", "Asignación inicial"
    MANUAL_UPGRADE = "manual_upgrade", "Upgrade manual"
    RE_ENROLLMENT = "re_enrollment", "Reincorporación"


class ProgressStatus(models.TextChoices):
    NOT_STARTED = "not_started", "No iniciado"
    IN_PROGRESS = "in_progress", "En progreso"
    COMPLETED = "completed", "Completado"


class UnitProgressStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "En progreso"
    COMPLETED = "completed", "Completada"


class LearningEventType(models.TextChoices):
    ENROLLMENT_CREATED = "enrollment_created", "Matrícula creada"
    ENROLLMENT_SUSPENDED = "enrollment_suspended", "Matrícula suspendida"
    ENROLLMENT_REACTIVATED = "enrollment_reactivated", "Matrícula reactivada"
    ENROLLMENT_REVOKED = "enrollment_revoked", "Matrícula revocada"
    RELEASE_ASSIGNED = "release_assigned", "Release asignado"
    RELEASE_UPGRADED = "release_upgraded", "Release actualizado"
    COURSE_STARTED = "course_started", "Curso iniciado"
    COURSE_COMPLETED = "course_completed", "Curso completado"
    COURSE_REOPENED = "course_reopened", "Curso reabierto"
    UNIT_OPENED = "unit_opened", "Unidad abierta"
    UNIT_COMPLETED = "unit_completed", "Unidad completada"
    UNIT_REOPENED = "unit_reopened", "Unidad reabierta"


class AccessState(models.TextChoices):
    AVAILABLE = "available", "Disponible"
    NOT_STARTED = "not_started", "Acceso no iniciado"
    ENDED = "ended", "Acceso finalizado"
    SUSPENDED = "suspended", "Suspendida"
    REVOKED = "revoked", "Revocada"
    PUBLICATION_WITHDRAWN = "publication_withdrawn", "Publicación retirada"
    MEMBERSHIP_INACTIVE = "membership_inactive", "Membresía inactiva"
    RELEASE_INVALID = "release_invalid", "Release inválido"
