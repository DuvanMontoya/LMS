from django.db import models


class LifecycleStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    ARCHIVED = "archived", "Archivado"


class AuthoringStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    IN_REVIEW = "in_review", "En revisión"
    CHANGES_REQUESTED = "changes_requested", "Cambios solicitados"
    APPROVED = "approved", "Aprobado"


class QuestionType(models.TextChoices):
    SINGLE_CHOICE = "single_choice", "Selección única"
    MULTIPLE_CHOICE = "multiple_choice", "Selección múltiple"
    TRUE_FALSE = "true_false", "Verdadero o falso"
    NUMERIC = "numeric", "Numérica"
    SHORT_TEXT = "short_text", "Texto corto"
    LONG_TEXT = "long_text", "Texto largo"
    ORDERING = "ordering", "Ordenamiento"
    MATCHING = "matching", "Emparejamiento"
    MATHEMATICAL_EXPRESSION = "mathematical_expression", "Expresión matemática"


class FeedbackMode(models.TextChoices):
    NONE = "none", "Sin retroalimentación"
    SCORE_ONLY = "score_only", "Sólo puntaje después de calificar"
    FULL_AFTER_GRADING = (
        "full_after_grading",
        "Retroalimentación completa después de calificar",
    )


class DeliveryStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    ACTIVE = "active", "Activa"
    WITHDRAWN = "withdrawn", "Retirada"


class AssignmentStatus(models.TextChoices):
    ACTIVE = "active", "Activa"
    REVOKED = "revoked", "Revocada"


class AttemptStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "En curso"
    GRADING_PENDING = "grading_pending", "Calificación automática pendiente"
    PENDING_MANUAL = "pending_manual", "Pendiente de calificación manual"
    GRADED = "graded", "Calificado"
    GRADING_FAILED = "grading_failed", "Falló la calificación"


class ResponseStatus(models.TextChoices):
    UNANSWERED = "unanswered", "Sin respuesta"
    SAVED = "saved", "Guardada"
    AUTO_GRADED = "auto_graded", "Calificada automáticamente"
    PENDING_MANUAL = "pending_manual", "Pendiente de calificación manual"
    MANUALLY_GRADED = "manually_graded", "Calificada manualmente"


class AttemptEventType(models.TextChoices):
    STARTED = "started", "Iniciado"
    RESPONSE_SAVED = "response_saved", "Respuesta guardada"
    SUBMITTED = "submitted", "Enviado"
    AUTO_GRADED = "auto_graded", "Calificado automáticamente"
    MANUAL_GRADED = "manual_graded", "Calificado manualmente"
    COMPLETED = "completed", "Completado"


class PoolSelectionStrategy(models.TextChoices):
    RANDOM_WITHOUT_REPLACEMENT = (
        "random_without_replacement",
        "Aleatoria sin reemplazo",
    )


class GradingRevisionSource(models.TextChoices):
    ORIGINAL = "original", "Original"
    CORRECTION = "correction", "Corrección"


class GradeSource(models.TextChoices):
    INITIAL = "initial", "Inicial"
    MANUAL_GRADE = "manual_grade", "Calificación manual"
    REGRADE = "regrade", "Recalificación"


class GradingStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PENDING_MANUAL = "pending_manual", "Pendiente de revisión manual"
    GRADED = "graded", "Calificado"
    FAILED = "failed", "Falló"


class JobStatus(models.TextChoices):
    QUEUED = "queued", "En cola"
    RUNNING = "running", "En ejecución"
    COMPLETED = "completed", "Completado"
    COMPLETED_WITH_ERRORS = "completed_with_errors", "Completado con errores"
    FAILED = "failed", "Falló"


class RegradeAttemptStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    PROCESSING = "processing", "Procesando"
    COMPLETED = "completed", "Completado"
    FAILED = "failed", "Falló"
    SKIPPED = "skipped", "Omitido"


class GradebookStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    ACTIVE = "active", "Activo"


class GradebookColumnStatus(models.TextChoices):
    ACTIVE = "active", "Activa"
    ARCHIVED = "archived", "Archivada"


class AttemptAggregation(models.TextChoices):
    HIGHEST = "highest", "Mejor intento"
    LATEST = "latest", "Último intento"


class GradebookEntryStatus(models.TextChoices):
    MISSING = "missing", "Sin entrega"
    PENDING = "pending", "Pendiente"
    GRADED = "graded", "Calificada"


class GradebookSummaryStatus(models.TextChoices):
    INCOMPLETE = "incomplete", "Incompleto"
    COMPLETE = "complete", "Completo"
