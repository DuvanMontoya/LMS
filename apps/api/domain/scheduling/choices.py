from django.db import models


class EventType(models.TextChoices):
    LIVE_CLASS = "live_class", "Clase en vivo"
    ACADEMIC_ACTIVITY = "academic_activity", "Actividad académica"


class SeriesStatus(models.TextChoices):
    ACTIVE = "active", "Activa"
    CANCELLED = "cancelled", "Cancelada"


class OccurrenceStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Programada"
    CANCELLED = "cancelled", "Cancelada"


class LiveSessionStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Programada"
    LIVE = "live", "En vivo"
    ENDED = "ended", "Finalizada"
    CANCELLED = "cancelled", "Cancelada"


class AttendanceRole(models.TextChoices):
    HOST = "host", "Profesor"
    STUDENT = "student", "Estudiante"
    ADMINISTRATOR = "administrator", "Administrador"


class WebhookProcessingStatus(models.TextChoices):
    PROCESSING = "processing", "Procesando"
    PROCESSED = "processed", "Procesado"
    FAILED = "failed", "Fallido"


class RecurrenceScope(models.TextChoices):
    OCCURRENCE = "occurrence", "Sólo esta clase"
    FOLLOWING = "following", "Esta clase y las siguientes"
    SERIES = "series", "Toda la serie"


class EgressStatus(models.TextChoices):
    DISABLED = "disabled", "Deshabilitada"
    IDLE = "idle", "Disponible"
    STARTING = "starting", "Iniciando"
    ACTIVE = "active", "Activa"
    ENDED = "ended", "Finalizada"
    FAILED = "failed", "Fallida"
