"""Restrict the official allauth URL tree to enabled account capabilities.

django-allauth 65.18.0 unconditionally exports phone URL patterns from its
browser headless tree. This project deliberately has no phone adapter or phone
authentication. Filtering the exported resolver tree keeps all official views
and names intact while making disabled routes unresolvable and absent from the
generated official schema.
"""

from __future__ import annotations

from collections.abc import Iterable
from importlib import import_module
from typing import cast

from django.urls.resolvers import URLPattern, URLResolver


def _without_phone_patterns(
    patterns: Iterable[URLPattern | URLResolver],
) -> list[URLPattern | URLResolver]:
    filtered: list[URLPattern | URLResolver] = []
    for pattern in patterns:
        if isinstance(pattern, URLPattern):
            if "phone" not in str(pattern.pattern):
                filtered.append(pattern)
            continue

        children = _without_phone_patterns(pattern.url_patterns)
        if not children:
            continue
        filtered.append(
            URLResolver(
                pattern.pattern,
                children,
                default_kwargs=pattern.default_kwargs,
                app_name=pattern.app_name,
                namespace=pattern.namespace,
            )
        )
    return filtered


app_name = "headless"
_upstream_module = import_module("allauth.headless.urls")
upstream_urlpatterns = cast(
    list[URLPattern | URLResolver], _upstream_module.urlpatterns
)
urlpatterns = _without_phone_patterns(upstream_urlpatterns)
