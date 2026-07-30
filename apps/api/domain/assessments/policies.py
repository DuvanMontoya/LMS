from __future__ import annotations

from typing import TYPE_CHECKING

from domain.organizations.capabilities import Capability
from domain.organizations.models import Organization
from domain.organizations.policies import has_capability

if TYPE_CHECKING:
    from domain.identity.models import User


def can_view_banks(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_BANK_VIEW)


def can_manage_banks(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_BANK_MANAGE)


def can_version_banks(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_BANK_VERSION)


def can_view_questions(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_QUESTION_VIEW)


def can_manage_questions(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_QUESTION_MANAGE)


def can_submit_questions(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_QUESTION_SUBMIT)


def can_review_questions(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_QUESTION_REVIEW)


def can_approve_questions(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_QUESTION_APPROVE)


def can_view_authoring(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_AUTHORING_VIEW)


def can_manage_authoring(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_AUTHORING_MANAGE)


def can_submit_authoring(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_AUTHORING_SUBMIT)


def can_review_authoring(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_AUTHORING_REVIEW)


def can_approve_authoring(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_AUTHORING_APPROVE)


def can_manage_deliveries(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_DELIVERY_MANAGE)


def can_view_deliveries(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_DELIVERY_VIEW)


def can_view_results(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_RESULTS_VIEW)


def can_grade_manually(actor: User | None, organization: Organization) -> bool:
    return has_capability(actor, organization, Capability.ASSESSMENT_GRADING_MANAGE)
