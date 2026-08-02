from django.db import models


class RoleCode(models.TextChoices):
    OWNER = "owner", "Propietario"
    ADMINISTRATOR = "administrator", "Administrador"
    AUTHOR = "author", "Autor"
    REVIEWER = "reviewer", "Revisor"
    INSTRUCTOR = "instructor", "Docente"
    LEARNER = "learner", "Estudiante"


class OrganizationStatus(models.TextChoices):
    PENDING_ACTIVATION = "pending_activation", "Pendiente de activación"
    ACTIVE = "active", "Activa"
    SUSPENDED = "suspended", "Suspendida"
    CLOSED = "closed", "Cerrada"


class MembershipStatus(models.TextChoices):
    ACTIVE = "active", "Activa"
    SUSPENDED = "suspended", "Suspendida"
    REVOKED = "revoked", "Revocada"


class MembershipEventType(models.TextChoices):
    CREATED = "membership_created", "Membresía creada"
    SUSPENDED = "membership_suspended", "Membresía suspendida"
    REACTIVATED = "membership_reactivated", "Membresía reactivada"
    REVOKED = "membership_revoked", "Membresía revocada"
    ROLE_ASSIGNED = "role_assigned", "Rol asignado"
    ROLE_REVOKED = "role_revoked", "Rol revocado"
    INVITATION_CREATED = "invitation_created", "Invitación creada"
    INVITATION_UPDATED = "invitation_updated", "Invitación actualizada"
    INVITATION_RESENT = "invitation_resent", "Invitación reenviada"
    INVITATION_REVOKED = "invitation_revoked", "Invitación revocada"
    INVITATION_ACCEPTED = "invitation_accepted", "Invitación aceptada"
    JOIN_REQUESTED = "join_requested", "Solicitud de ingreso creada"
    JOIN_APPROVED = "join_approved", "Solicitud de ingreso aprobada"
    JOIN_REJECTED = "join_rejected", "Solicitud de ingreso rechazada"
    MANAGED_ACCOUNT_CREATED = "managed_account_created", "Cuenta administrada creada"
    MANAGED_ACCOUNT_ACTIVATED = (
        "managed_account_activated",
        "Cuenta administrada activada",
    )
    PROFILE_UPDATED = "profile_updated", "Perfil institucional actualizado"
    ROLES_REPLACED = "roles_replaced", "Roles sustituidos"
    SESSIONS_REVOKED = "sessions_revoked", "Sesiones revocadas"
    PASSWORD_RECOVERY_SENT = (
        "password_recovery_sent",
        "Recuperación de contraseña enviada",
    )
    SETTINGS_UPDATED = (
        "membership_settings_updated",
        "Configuración de membresías actualizada",
    )


class InvitationType(models.TextChoices):
    EXISTING_USER = "existing_user", "Usuario existente"
    NEW_USER = "new_user", "Usuario nuevo"
    MANAGED_ACCOUNT = "managed_account", "Cuenta administrada"
    INITIAL_OWNER = "initial_owner", "Propietario inicial"


class InvitationStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    ACCEPTED = "accepted", "Aceptada"
    REVOKED = "revoked", "Revocada"
    EXPIRED = "expired", "Expirada"


class JoinRequestStatus(models.TextChoices):
    PENDING = "pending", "Pendiente"
    APPROVED = "approved", "Aprobada"
    REJECTED = "rejected", "Rechazada"
    CANCELLED = "cancelled", "Cancelada"


class MemberType(models.TextChoices):
    LEARNER = "learner", "Estudiante"
    INSTRUCTOR = "instructor", "Docente"
    GUARDIAN = "guardian", "Acudiente"
    ADMINISTRATIVE = "administrative", "Personal administrativo"
    SUPPORT = "support", "Personal de apoyo"
    OTHER = "other", "Otro"


def normalize_member_type(value: str) -> str:
    normalized = value.strip().lower()
    aliases = {
        "student": MemberType.LEARNER,
        "estudiante": MemberType.LEARNER,
        "teacher": MemberType.INSTRUCTOR,
        "profesor": MemberType.INSTRUCTOR,
        "docente": MemberType.INSTRUCTOR,
        "staff": MemberType.ADMINISTRATIVE,
    }
    return str(aliases.get(normalized, normalized))


class DocumentType(models.TextChoices):
    CIVIL_REGISTRY = "RC", "Registro civil"
    IDENTITY_CARD = "TI", "Tarjeta de identidad"
    CITIZENSHIP_CARD = "CC", "Cédula de ciudadanía"
    FOREIGNER_CARD = "CE", "Cédula de extranjería"
    TEMPORARY_PROTECTION = "PPT", "Permiso por protección temporal"
    PASSPORT = "PA", "Pasaporte"
    FOREIGN_DOCUMENT = "DE", "Documento extranjero"
    NONE = "NONE", "Sin documento registrado"


class Gender(models.TextChoices):
    FEMALE = "female", "Femenino"
    MALE = "male", "Masculino"
    NON_BINARY = "non_binary", "No binario"
    OTHER = "other", "Otro"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefiero no responder"


class EducationStage(models.TextChoices):
    PRESCHOOL = "preschool", "Preescolar"
    SCHOOL = "school", "Colegio"
    TECHNICAL = "technical", "Institución técnica o tecnológica"
    UNIVERSITY = "university", "Universidad"
    GRADUATED = "graduated", "Graduado"
    NOT_STUDYING = "not_studying", "Actualmente no estudia"
    OTHER = "other", "Otra situación"


class EducationLevel(models.TextChoices):
    PRESCHOOL = "preschool", "Preescolar"
    GRADE_1 = "grade_1", "1.º"
    GRADE_2 = "grade_2", "2.º"
    GRADE_3 = "grade_3", "3.º"
    GRADE_4 = "grade_4", "4.º"
    GRADE_5 = "grade_5", "5.º"
    GRADE_6 = "grade_6", "6.º"
    GRADE_7 = "grade_7", "7.º"
    GRADE_8 = "grade_8", "8.º"
    GRADE_9 = "grade_9", "9.º"
    GRADE_10 = "grade_10", "10.º"
    GRADE_11 = "grade_11", "11.º"
    TECHNICAL = "technical", "Técnico profesional"
    TECHNOLOGIST = "technologist", "Tecnólogo"
    UNDERGRADUATE = "undergraduate", "Pregrado universitario"
    SPECIALIZATION = "specialization", "Especialización"
    MASTERS = "masters", "Maestría"
    DOCTORATE = "doctorate", "Doctorado"
    NOT_APPLICABLE = "not_applicable", "No aplica"


class SocioeconomicStratum(models.TextChoices):
    NOT_REPORTED = "not_reported", "Prefiere no informar"
    RURAL = "rural", "Rural o sin estratificación"
    ONE = "1", "Estrato 1"
    TWO = "2", "Estrato 2"
    THREE = "3", "Estrato 3"
    FOUR = "4", "Estrato 4"
    FIVE = "5", "Estrato 5"
    SIX = "6", "Estrato 6"


class RegistrationReason(models.TextChoices):
    COURSE = "course", "Tomar un curso"
    SCHOOL_SUPPORT = "school_support", "Refuerzo escolar"
    EXAM_PREPARATION = "exam_preparation", "Preparación para una evaluación"
    PROFESSIONAL_DEVELOPMENT = "professional_development", "Formación profesional"
    TEACHING = "teaching", "Enseñar o acompañar estudiantes"
    INSTITUTIONAL = "institutional", "Vinculación institucional"
    OTHER = "other", "Otro motivo"
