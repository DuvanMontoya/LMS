from __future__ import annotations

import csv
import io
import uuid
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from .capabilities import Capability
from .choices import RoleCode
from .exceptions import OrganizationAccessDenied
from .policies import has_capability
from .services import invite_person

if TYPE_CHECKING:
    from django.core.files.uploadedfile import UploadedFile

    from domain.identity.models import User
    from domain.organizations.models import Organization


MAX_BULK_INVITATION_ROWS = 500
MAX_BULK_INVITATION_BYTES = 512_000
_REQUIRED_COLUMNS = frozenset(
    {"email", "given_name", "family_name", "member_type", "institutional_id", "roles"}
)
_PREVIEW_SESSION_KEY = "organization_bulk_invitation_preview"

# UploadedFile and Django session mappings are dynamically typed by upstream.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportOptionalOperand=false


@dataclass(frozen=True)
class BulkInvitationIssue:
    row: int
    field: str
    message: str


def _error(row: int, field: str, message: str) -> BulkInvitationIssue:
    return BulkInvitationIssue(row=row, field=field, message=message)


def parse_bulk_invitation_csv(
    upload: UploadedFile,
) -> tuple[list[dict[str, object]], list[BulkInvitationIssue]]:
    if (upload.size or 0) > MAX_BULK_INVITATION_BYTES:
        return [], [_error(0, "file", "El archivo supera el límite permitido.")]
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [_error(0, "file", "El archivo debe usar UTF-8.")]
    reader = csv.DictReader(io.StringIO(text))
    fields = set(reader.fieldnames or [])
    if fields != set(_REQUIRED_COLUMNS):
        return [], [
            _error(
                0,
                "file",
                "Las columnas deben ser email, given_name, family_name, member_type, institutional_id y roles.",
            )
        ]
    rows = list(reader)
    if not rows:
        return [], [_error(0, "file", "El archivo no contiene invitaciones.")]
    if len(rows) > MAX_BULK_INVITATION_ROWS:
        return [], [_error(0, "file", "El máximo es de 500 filas.")]

    valid: list[dict[str, object]] = []
    issues: list[BulkInvitationIssue] = []
    seen_emails: set[str] = set()
    for number, raw in enumerate(rows, start=2):
        email = str(raw.get("email") or "").strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            issues.append(_error(number, "email", "Correo inválido."))
            continue
        if email in seen_emails:
            issues.append(_error(number, "email", "Correo repetido en el archivo."))
            continue
        seen_emails.add(email)
        role_values = [item.strip() for item in str(raw.get("roles") or "").split("|")]
        try:
            roles = {RoleCode(item) for item in role_values if item}
        except ValueError:
            issues.append(_error(number, "roles", "Hay un rol inválido."))
            continue
        if not roles:
            issues.append(_error(number, "roles", "Debes indicar al menos un rol."))
            continue
        if RoleCode.OWNER in roles:
            issues.append(_error(number, "roles", "Owner no puede importarse."))
            continue
        valid.append(
            {
                "email": email,
                "given_name": str(raw.get("given_name") or "").strip(),
                "family_name": str(raw.get("family_name") or "").strip(),
                "member_type": str(raw.get("member_type") or "").strip(),
                "institutional_id": str(raw.get("institutional_id") or "").strip(),
                "roles": sorted(role.value for role in roles),
            }
        )
    return valid, issues


def create_bulk_invitation_preview(
    *, request: object, actor: User, organization: Organization, upload: UploadedFile
) -> dict[str, object]:
    if not has_capability(actor, organization, Capability.MEMBERSHIP_INVITE):
        raise OrganizationAccessDenied("No tienes permiso para invitar personas.")
    if not organization.membership_settings.allow_bulk_invitations:
        raise OrganizationAccessDenied(
            "La institución no permite importaciones masivas."
        )
    valid, issues = parse_bulk_invitation_csv(upload)
    preview_id = str(uuid.uuid4())
    session = request.session  # type: ignore[attr-defined]
    session[_PREVIEW_SESSION_KEY] = {
        "id": preview_id,
        "organization_id": str(organization.id),
        "actor_id": str(actor.id),
        "valid_rows": valid,
        "issues": [asdict(issue) for issue in issues],
        "created_at": timezone.now().isoformat(),
    }
    session.modified = True
    return {
        "preview_id": preview_id,
        "valid_count": len(valid),
        "issues": [asdict(issue) for issue in issues],
    }


@transaction.atomic
def confirm_bulk_invitation_preview(
    *, request: object, actor: User, organization: Organization, preview_id: str
) -> int:
    if not has_capability(actor, organization, Capability.MEMBERSHIP_INVITE):
        raise OrganizationAccessDenied("No tienes permiso para invitar personas.")
    if not organization.membership_settings.allow_bulk_invitations:
        raise OrganizationAccessDenied(
            "La institución no permite importaciones masivas."
        )
    session = request.session  # type: ignore[attr-defined]
    preview = session.get(_PREVIEW_SESSION_KEY)
    if not isinstance(preview, dict):
        raise OrganizationAccessDenied("La vista previa ya no está disponible.")
    if (
        preview.get("id") != preview_id
        or preview.get("organization_id") != str(organization.id)
        or preview.get("actor_id") != str(actor.id)
        or preview.get("issues")
    ):
        raise OrganizationAccessDenied("La vista previa no puede confirmarse.")
    rows = preview.get("valid_rows")
    if not isinstance(rows, list) or not rows:
        raise OrganizationAccessDenied(
            "La vista previa no contiene invitaciones válidas."
        )
    for row in rows:
        if not isinstance(row, dict):
            raise OrganizationAccessDenied("La vista previa no es válida.")
        invite_person(
            actor=actor,
            organization=organization,
            email=str(row["email"]),
            roles={RoleCode(role) for role in row["roles"]},  # type: ignore[arg-type]
            given_name=str(row["given_name"]),
            family_name=str(row["family_name"]),
            member_type=str(row["member_type"]),
            institutional_id=str(row["institutional_id"]),
        )
    session.pop(_PREVIEW_SESSION_KEY, None)
    session.modified = True
    return len(rows)
