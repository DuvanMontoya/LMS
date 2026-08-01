from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Comprueba conexión TLS y autenticación SMTP sin enviar un correo."

    def handle(self, *args: object, **options: object) -> None:
        expected_backend = "django.core.mail.backends.smtp.EmailBackend"
        if settings.EMAIL_BACKEND != expected_backend:
            raise CommandError(
                "EMAIL_BACKEND no es SMTP; activa EMAIL_DELIVERY_MODE=smtp."
            )
        connection = get_connection(fail_silently=False)
        try:
            connection.open()
        except Exception as error:
            raise CommandError(
                f"Falló la conexión o autenticación SMTP ({type(error).__name__})."
            ) from error
        finally:
            connection.close()
        self.stdout.write(
            self.style.SUCCESS(
                f"SMTP autenticado correctamente en {settings.EMAIL_HOST}:"
                f"{settings.EMAIL_PORT}; no se envió ningún correo."
            )
        )
