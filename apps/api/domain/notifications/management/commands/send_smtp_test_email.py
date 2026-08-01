import uuid
from argparse import ArgumentParser

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email


class Command(BaseCommand):
    help = "Envía un único correo SMTP de comprobación a un destinatario autorizado."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--to", required=True)
        parser.add_argument("--confirm", action="store_true")

    def handle(self, *args: object, **options: object) -> None:
        if not options.get("confirm"):
            raise CommandError(
                "Se requiere --confirm para transmitir el correo de prueba."
            )
        expected_backend = "django.core.mail.backends.smtp.EmailBackend"
        if settings.EMAIL_BACKEND != expected_backend:
            raise CommandError(
                "EMAIL_BACKEND no es SMTP; activa EMAIL_DELIVERY_MODE=smtp."
            )
        recipient = str(options["to"]).strip().lower()
        try:
            validate_email(recipient)
        except ValidationError as error:
            raise CommandError("El destinatario de prueba no es válido.") from error
        message = EmailMultiAlternatives(
            subject="Prueba de correo de Plataforma Académica",
            body=(
                "La integración SMTP de Plataforma Académica funciona correctamente.\n\n"
                "Este mensaje fue solicitado como una prueba local y no requiere respuesta."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
            headers={"Resend-Idempotency-Key": f"smtp-smoke-{uuid.uuid4()}"},
        )
        message.attach_alternative(
            """<!doctype html>
<html lang="es"><body style="font-family:Arial,Helvetica,sans-serif;color:#182230">
<h1>Correo configurado correctamente</h1>
<p>La integración SMTP de Plataforma Académica funciona correctamente.</p>
<p>Este mensaje fue solicitado como una prueba local y no requiere respuesta.</p>
</body></html>""",
            "text/html",
        )
        sent = message.send(fail_silently=False)
        if sent != 1:
            raise CommandError("El backend SMTP no confirmó la transmisión.")
        self.stdout.write(self.style.SUCCESS("Correo de prueba transmitido."))
