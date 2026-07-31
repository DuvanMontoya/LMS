from django.conf import settings


def assessment_queue(name: str) -> str:
    prefix = settings.ASSESSMENT_TASK_QUEUE_PREFIX
    return f"{prefix}{name}"


def assessment_task_options(name: str) -> dict[str, object]:
    options: dict[str, object] = {"queue": assessment_queue(name)}
    countdown = settings.ASSESSMENT_TASK_COUNTDOWN_SECONDS
    if countdown:
        options["countdown"] = countdown
    return options
