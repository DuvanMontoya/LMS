class CourseDomainError(Exception):
    """Error de dominio seguro que sólo se traduce en el borde HTTP."""


class CourseAccessDenied(CourseDomainError):
    pass


class CourseNotFound(CourseDomainError):
    pass


class CourseArchived(CourseDomainError):
    pass


class CourseSlugReserved(CourseDomainError):
    pass


class CourseSlugImmutable(CourseDomainError):
    pass


class CourseRevisionNotEditable(CourseDomainError):
    pass


class CourseRevisionConflict(CourseDomainError):
    pass


class CourseRevisionTransitionInvalid(CourseDomainError):
    pass


class CourseRevisionNotReady(CourseDomainError):
    def __init__(self, issues: list[dict[str, str]]) -> None:
        super().__init__("La revisión no está lista.")
        self.issues = issues


class CourseRevisionAlreadyOpen(CourseDomainError):
    pass


class CourseStructureInvalid(CourseDomainError):
    pass


class CourseModuleNotFound(CourseDomainError):
    pass


class CourseUnitNotFound(CourseDomainError):
    pass


class CourseOrderInvalid(CourseDomainError):
    pass


class CourseCurriculumAlignmentInvalid(CourseDomainError):
    pass


class CourseCrossOrganizationRelation(CourseDomainError):
    pass


class CourseArchivedCatalogReference(CourseDomainError):
    pass


class CourseLimitExceeded(CourseDomainError):
    pass
