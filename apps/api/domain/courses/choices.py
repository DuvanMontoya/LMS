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


class ActivityType(models.TextChoices):
    LESSON = "lesson", "Lección"
    LIVE_CLASS = "live_class", "Clase en vivo"
    ASSESSMENT = "assessment", "Evaluación"


class LessonKind(models.TextChoices):
    DOCUMENT = "document", "Documento"
    MEDIACMS_VIDEO = "mediacms_video", "Video MediaCMS"
    LATEX_SOURCE = "latex_source", "Archivo LaTeX (.tex)"
    MARKDOWN_SOURCE = "markdown_source", "Archivo Markdown (.md)"
    PDF = "pdf", "PDF"
    SLIDES = "slides", "Diapositivas"
    AUDIO = "audio", "Audio"


class ActivityCompletionMethod(models.TextChoices):
    VIEW = "view", "Ver la actividad"
    MANUAL = "manual", "Marcación explícita"
    ATTENDANCE = "attendance", "Cumplir asistencia"
    SUBMISSION = "submission", "Enviar intento"
    GRADE = "grade", "Recibir calificación"
    PASS = "pass", "Aprobar"


class AvailabilityRuleType(models.TextChoices):
    ACTIVITY_COMPLETED = "activity_completed", "Actividad completada"
    ACTIVITY_PASSED = "activity_passed", "Actividad aprobada"
    MINIMUM_GRADE = "minimum_grade", "Calificación mínima"
    OBJECTIVE_MASTERED = "objective_mastered", "Objetivo dominado"
    AVAILABLE_FROM = "available_from", "Disponible desde"
    AVAILABLE_UNTIL = "available_until", "Disponible hasta"
