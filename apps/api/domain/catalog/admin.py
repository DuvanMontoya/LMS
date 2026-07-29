# pyright: reportMissingTypeArgument=false
from django.contrib import admin

from .models import (
    AcademicArea,
    Concept,
    Discipline,
    LearningObjective,
    Subject,
    Topic,
)


@admin.register(AcademicArea, Discipline, Subject, Concept)
class CatalogEntityAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    readonly_fields = ("id", "created_at", "updated_at", "archived_at")


@admin.register(LearningObjective)
class LearningObjectiveAdmin(admin.ModelAdmin):
    list_display = ("code", "subject", "cognitive_level", "status", "updated_at")
    list_filter = ("status", "cognitive_level")
    search_fields = ("code", "statement", "subject__name")
    readonly_fields = ("id", "created_at", "updated_at", "archived_at")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "depth", "status", "updated_at")
    list_filter = ("status", "subject")
    search_fields = ("title", "slug", "subject__name")
    readonly_fields = ("id", "path", "depth", "numchild", "created_at", "updated_at")
