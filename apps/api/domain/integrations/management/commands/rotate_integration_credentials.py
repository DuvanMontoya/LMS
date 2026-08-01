from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from domain.integrations.crypto import (
    CredentialConfigurationError,
    CredentialDecryptionError,
    EncryptedValue,
    connection_aad,
    decrypt,
    encrypt,
)
from domain.integrations.models import IntegrationCredential

# Django management and ORM APIs are dynamic in django-stubs.
# pyright: reportMissingParameterType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false


class Command(BaseCommand):
    help = "Re-cifra credenciales de integraciones con la clave maestra activa."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options) -> None:
        dry_run = bool(options["dry_run"])
        rotated = 0
        try:
            with transaction.atomic():
                credentials = (
                    IntegrationCredential.objects.select_for_update().select_related(
                        "connection__organization"
                    )
                )
                for credential in credentials.iterator():
                    connection = credential.connection
                    aad = connection_aad(
                        organization_id=connection.organization_id,
                        provider=connection.provider,
                        connection_id=connection.id,
                    )
                    plaintext = decrypt(
                        encrypted=EncryptedValue(
                            key_id=credential.key_id,
                            nonce=bytes(credential.nonce),
                            ciphertext=bytes(credential.ciphertext),
                        ),
                        aad=aad,
                    )
                    replacement = encrypt(plaintext=plaintext, aad=aad)
                    if (
                        replacement.key_id == credential.key_id
                        and replacement.ciphertext == bytes(credential.ciphertext)
                    ):
                        continue
                    rotated += 1
                    if not dry_run:
                        credential.key_id = replacement.key_id
                        credential.nonce = replacement.nonce
                        credential.ciphertext = replacement.ciphertext
                        credential.save(
                            update_fields=(
                                "key_id",
                                "nonce",
                                "ciphertext",
                                "rotated_at",
                            )
                        )
                if dry_run:
                    transaction.set_rollback(True)
        except (CredentialConfigurationError, CredentialDecryptionError) as error:
            raise CommandError(
                "La clave maestra de integraciones no es válida."
            ) from error
        mode = "simuladas" if dry_run else "rotadas"
        self.stdout.write(self.style.SUCCESS(f"Credenciales {mode}: {rotated}."))
