class SchedulingDomainError(Exception):
    code = "scheduling_error"
    status_code = 400


class SchedulingAccessDenied(SchedulingDomainError):
    code = "scheduling_permission_denied"
    status_code = 403


class SchedulingNotFound(SchedulingDomainError):
    code = "scheduling_not_found"
    status_code = 404


class SchedulingConflict(SchedulingDomainError):
    code = "scheduling_conflict"
    status_code = 409


class SchedulingInvalid(SchedulingDomainError):
    code = "scheduling_invalid"
    status_code = 400


class LiveKitUnavailable(SchedulingDomainError):
    code = "livekit_unavailable"
    status_code = 503


class LiveKitRejected(SchedulingDomainError):
    code = "livekit_rejected"
    status_code = 502


class LiveSessionOutsideWindow(SchedulingDomainError):
    code = "live_session_outside_window"
    status_code = 409


class LiveSessionClosed(SchedulingDomainError):
    code = "live_session_closed"
    status_code = 409


class LiveKitWebhookInvalid(SchedulingDomainError):
    code = "livekit_webhook_invalid"
    status_code = 401
