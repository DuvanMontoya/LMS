from django.db import models


class PublicationStatus(models.TextChoices):
    ACTIVE = "active", "Activa"
    WITHDRAWN = "withdrawn", "Retirada"


class PublicationEventType(models.TextChoices):
    RELEASE_PUBLISHED = "release_published", "Release publicado"
    PUBLICATION_WITHDRAWN = "publication_withdrawn", "Publicación retirada"
    DRAFT_CREATED_FROM_RELEASE = (
        "draft_created_from_release",
        "Draft creado desde release",
    )
