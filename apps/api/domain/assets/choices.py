from django.db import models


class AssetKind(models.TextChoices):
    IMAGE = "image", "Imagen"
    DOCUMENT = "document", "Documento"
    AUDIO = "audio", "Audio"
    VIDEO = "video", "Video"
    DATASET = "dataset", "Dataset"
    CAPTION = "caption", "Captions"


class AssetStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    ARCHIVED = "archived", "Archivado"


class AssetVersionStatus(models.TextChoices):
    PENDING_UPLOAD = "pending_upload", "Pendiente de carga"
    UPLOADED = "uploaded", "Cargado"
    SCANNING = "scanning", "Escaneando"
    PROCESSING = "processing", "Procesando"
    READY = "ready", "Listo"
    REJECTED = "rejected", "Rechazado"
    FAILED = "failed", "Fallido"


class VariantRole(models.TextChoices):
    IMAGE_THUMBNAIL = "image_thumbnail", "Miniatura"
    IMAGE_MEDIUM = "image_medium", "Imagen mediana"
    IMAGE_LARGE = "image_large", "Imagen grande"
    IMAGE_WEB_FALLBACK = "image_web_fallback", "Fallback web"
    AUDIO_PLAYBACK = "audio_playback", "Audio reproducible"
    VIDEO_PLAYBACK = "video_playback", "Video reproducible"
    VIDEO_POSTER = "video_poster", "Poster de video"
    CAPTION_NORMALIZED = "caption_normalized", "Captions normalizados"


class UploadMethod(models.TextChoices):
    SINGLE = "single", "Simple"
    MULTIPART = "multipart", "Multipart"


class UploadStatus(models.TextChoices):
    INITIATED = "initiated", "Iniciada"
    UPLOADING = "uploading", "Cargando"
    UPLOADED = "uploaded", "Cargada"
    COMPLETED = "completed", "Completada"
    ABORTED = "aborted", "Abortada"
    EXPIRED = "expired", "Expirada"
    FAILED = "failed", "Fallida"


class ProcessingJobType(models.TextChoices):
    INITIAL = "initial_processing", "Procesamiento inicial"
    REPROCESS = "reprocess_variants", "Reprocesar variantes"


class ProcessingJobStatus(models.TextChoices):
    QUEUED = "queued", "En cola"
    RUNNING = "running", "En ejecución"
    COMPLETED = "completed", "Completado"
    COMPLETED_WITH_ERRORS = "completed_with_errors", "Completado con errores"
    FAILED = "failed", "Fallido"


class ProcessingStage(models.TextChoices):
    QUEUED = "queued", "En cola"
    DOWNLOADING = "downloading", "Descargando"
    SCANNING = "scanning", "Escaneando"
    VALIDATING = "validating", "Validando"
    EXTRACTING_METADATA = "extracting_metadata", "Extrayendo metadatos"
    TRANSCODING = "transcoding", "Transcodificando"
    UPLOADING_VARIANTS = "uploading_variants", "Subiendo variantes"
    PROMOTING_ORIGINAL = "promoting_original", "Promoviendo original"
    CLEANING_QUARANTINE = "cleaning_quarantine", "Limpiando cuarentena"
    COMPLETED = "completed", "Completado"


class AssetEventType(models.TextChoices):
    ASSET_CREATED = "asset_created", "Asset creado"
    UPLOAD_INITIALIZED = "upload_initialized", "Carga iniciada"
    UPLOAD_COMPLETED = "upload_completed", "Carga completada"
    MALWARE_SCAN_PASSED = "malware_scan_passed", "Antivirus aprobado"
    MALWARE_DETECTED = "malware_detected", "Malware detectado"
    VALIDATION_PASSED = "validation_passed", "Validación aprobada"
    VALIDATION_FAILED = "validation_failed", "Validación fallida"
    PROCESSING_STARTED = "processing_started", "Procesamiento iniciado"
    PROCESSING_COMPLETED = "processing_completed", "Procesamiento completado"
    PROCESSING_FAILED = "processing_failed", "Procesamiento fallido"
    VERSION_PROMOTED = "version_promoted", "Versión promovida"
    ASSET_ARCHIVED = "asset_archived", "Asset archivado"
    ASSET_RESTORED = "asset_restored", "Asset restaurado"
    REPROCESS_REQUESTED = "reprocess_requested", "Reprocesamiento solicitado"
