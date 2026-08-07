# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportPrivateUsage=false
import uuid
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from domain.organizations.choices import RoleCode
from domain.organizations.services import (
    add_existing_member_with_roles,
    create_organization_with_owner,
)

from .indexers import SearchDocumentDTO
from .models import (
    GenerationStatus,
    SearchAudience,
    SearchGeneration,
    SearchIndexJob,
    SearchIndexJobStatus,
    SearchIndexOperation,
    SearchSourceType,
)
from .normalization import normalize_query, normalize_title
from .services import (
    rebuild_search_index,
    search_authorized_documents,
    suggest_authorized_documents,
    upsert_search_document,
)
from .snippets import safe_snippet
from .tasks import process_search_index_job


class DiscoveryTests(TestCase):
    def setUp(self) -> None:
        self.owner = get_user_model().objects.create_user(
            email="search-owner@example.test", password="StrongSearchPassword!42"
        )
        self.organization = create_organization_with_owner(
            actor=self.owner, name="Búsqueda", slug="busqueda"
        )
        self.author = get_user_model().objects.create_user(
            email="search-author@example.test", password="StrongSearchPassword!42"
        )
        EmailAddress.objects.create(
            user=self.author,
            email=self.author.email,
            verified=True,
            primary=True,
        )
        add_existing_member_with_roles(
            actor=self.owner,
            organization=self.organization,
            user=self.author,
            roles={RoleCode.AUTHOR},
        )
        self.administrator = get_user_model().objects.create_user(
            email="search-administrator@example.test",
            password="StrongSearchPassword!42",
        )
        EmailAddress.objects.create(
            user=self.administrator,
            email=self.administrator.email,
            verified=True,
            primary=True,
        )
        add_existing_member_with_roles(
            actor=self.owner,
            organization=self.organization,
            user=self.administrator,
            roles={RoleCode.ADMINISTRATOR},
        )
        self.generation = SearchGeneration.objects.create(
            organization=self.organization,
            number=1,
            status=GenerationStatus.ACTIVE,
            started_at=timezone.now(),
            completed_at=timezone.now(),
            created_by=self.owner,
        )

    def document(self) -> SearchDocumentDTO:
        return SearchDocumentDTO(
            source_type=SearchSourceType.CATALOG_CONCEPT,
            source_id=uuid.uuid4(),
            source_version_id=None,
            audience=SearchAudience.AUTHORING,
            language="es",
            title="Álgebra lineal",
            subtitle="Matemáticas",
            body="Vectores, matrices y transformaciones lineales.",
            url_path=f"/organizaciones/{self.organization.slug}/curriculo/conceptos",
            metadata={},
        )

    def test_normalization_limits_and_safe_segmented_snippet(self) -> None:
        self.assertEqual(normalize_query("  álgebra   lineal "), "álgebra lineal")
        self.assertEqual(normalize_title("ÁLGEBRA"), "algebra")
        with self.assertRaises(ValueError):
            normalize_query("x")
        segments = safe_snippet("<script>alert(1)</script> álgebra", "álgebra")
        self.assertIn("<script>", "".join(item.text for item in segments))
        self.assertTrue(any(item.highlighted for item in segments))

    def test_digest_noop_typo_and_cross_organization_authorization(self) -> None:
        dto = self.document()
        upsert_search_document(self.generation, dto)
        document = self.generation.documents.get()
        indexed_at = document.indexed_at
        upsert_search_document(self.generation, dto)
        document.refresh_from_db()
        self.assertEqual(document.indexed_at, indexed_at)
        self.generation.documents.filter(pk=document.pk).update(is_active=False)
        upsert_search_document(self.generation, dto)
        document.refresh_from_db()
        self.assertTrue(document.is_active)
        self.assertEqual(document.indexed_at, indexed_at)
        result = search_authorized_documents(
            actor=self.author, organization=self.organization, query="algeba"
        )
        self.assertEqual(result.total, 1)
        suggestions = suggest_authorized_documents(
            actor=self.author, organization=self.organization, query="algebr linel"
        )
        self.assertEqual(suggestions[0]["title"], "Álgebra lineal")

        outsider = get_user_model().objects.create_user(
            email="search-outsider@example.test", password="StrongSearchPassword!42"
        )
        forbidden = search_authorized_documents(
            actor=outsider, organization=self.organization, query="algebra"
        )
        self.assertEqual(forbidden.total, 0)
        self.assertEqual(
            suggest_authorized_documents(
                actor=outsider, organization=self.organization, query="algebr linel"
            ),
            [],
        )

    def test_search_and_index_operations_api(self) -> None:
        upsert_search_document(self.generation, self.document())
        client = APIClient()
        client.force_authenticate(user=self.author)
        base = f"/api/v1/organizations/{self.organization.slug}/search/"
        response = client.get(base, {"q": "álgebra"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["pagination"]["total"], 1)
        self.assertEqual(client.get(base, {"q": "x"}).status_code, 400)
        self.assertEqual(
            client.get(base, {"q": "álgebra", "types": "bad"}).status_code, 400
        )
        suggestions = client.get(f"{base}suggestions/", {"q": "algebr linel"})
        self.assertEqual(suggestions.status_code, 200)
        self.assertEqual(suggestions.data[0]["title"], "Álgebra lineal")
        index_client = APIClient()
        index_client.force_authenticate(user=self.administrator)
        self.assertEqual(
            index_client.get("/api/v1/platform/search-index/").status_code, 200
        )
        self.assertEqual(
            index_client.get("/api/v1/platform/search-index/jobs/").status_code, 200
        )
        with patch(
            "domain.discovery.api.views.process_search_index_job.delay"
        ) as delay:
            with self.captureOnCommitCallbacks(execute=True):
                rebuild = index_client.post(
                    "/api/v1/platform/search-index/rebuild/",
                    {"organization_slug": self.organization.slug},
                    format="json",
                )
        self.assertEqual(rebuild.status_code, 202)
        delay.assert_called_once()
        self.assertEqual(
            index_client.post(
                "/api/v1/platform/search-index/rebuild/",
                {"organization_slug": self.organization.slug},
                format="json",
            ).status_code,
            409,
        )

    def test_platform_operator_without_membership_cannot_list_foreign_index_data(
        self,
    ) -> None:
        SearchIndexJob.objects.create(
            organization=self.organization,
            source_type=SearchSourceType.COURSE_RELEASE,
            operation=SearchIndexOperation.REBUILD,
        )
        operator = get_user_model().objects.create_superuser(
            email="search-operator@example.test", password="StrongSearchPassword!42"
        )
        client = APIClient()
        client.force_authenticate(user=operator)

        generations = client.get("/api/v1/platform/search-index/")
        jobs = client.get("/api/v1/platform/search-index/jobs/")

        self.assertEqual(generations.status_code, 200)
        self.assertEqual(generations.data, [])
        self.assertEqual(jobs.status_code, 200)
        self.assertEqual(jobs.data, [])

    def test_rebuild_generations_and_task_lifecycle(self) -> None:
        with patch(
            "domain.discovery.services.organization_documents",
            return_value=[self.document()],
        ):
            rebuilt = rebuild_search_index(
                organization=self.organization, actor=self.owner
            )
        self.generation.refresh_from_db()
        self.assertEqual(self.generation.status, GenerationStatus.SUPERSEDED)
        self.assertEqual(rebuilt.status, GenerationStatus.ACTIVE)
        self.assertEqual(rebuilt.document_count, 1)

        with (
            patch(
                "domain.discovery.services.organization_documents",
                side_effect=RuntimeError("index failure"),
            ),
            self.assertRaises(RuntimeError),
        ):
            rebuild_search_index(organization=self.organization, actor=self.owner)
        self.assertTrue(
            SearchGeneration.objects.filter(
                organization=self.organization,
                status=GenerationStatus.FAILED,
                failure_code="rebuild_failed",
            ).exists()
        )

        job = SearchIndexJob.objects.create(
            organization=self.organization,
            source_type=SearchSourceType.COURSE_RELEASE,
            operation=SearchIndexOperation.REBUILD,
        )
        with patch("domain.discovery.tasks.rebuild_search_index", return_value=rebuilt):
            process_search_index_job(str(job.id))
        job.refresh_from_db()
        self.assertEqual(job.status, SearchIndexJobStatus.COMPLETED)
        process_search_index_job(str(job.id))

        failed = SearchIndexJob.objects.create(
            organization=self.organization,
            source_type=SearchSourceType.COURSE_RELEASE,
            operation=SearchIndexOperation.REBUILD,
        )
        with (
            patch(
                "domain.discovery.tasks.rebuild_search_index",
                side_effect=RuntimeError("boom"),
            ),
            self.assertRaises(RuntimeError),
        ):
            process_search_index_job(str(failed.id))
        failed.refresh_from_db()
        self.assertEqual(failed.status, SearchIndexJobStatus.FAILED)
