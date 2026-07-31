from __future__ import annotations

from unittest import TestCase

from domain.content.exceptions import (
    ContentDuplicateNodeId,
    ContentNodeLimitExceeded,
    ContentSchemaInvalid,
    ContentSchemaUnsupported,
    ContentTooDeep,
    ContentTooLarge,
    ContentUnsafeLink,
    ContentUnsafeMath,
)
from domain.content.extraction import has_meaningful_content
from domain.content.validators import validate_content, validate_schema_contract

from .support import empty_document, full_document


class ContentSchemaTests(TestCase):
    def test_schema_and_complete_fixture_are_valid_and_deterministic(self) -> None:
        validate_schema_contract()
        first = validate_content(full_document(), schema_version=1)
        second = validate_content(full_document(), schema_version=1)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(len(first.digest), 64)
        self.assertGreater(first.metrics.node_count, 10)
        self.assertIn("f(x)=x^2", first.metrics.plain_text)
        self.assertTrue(has_meaningful_content(first.content))
        self.assertFalse(has_meaningful_content(empty_document()))

    def test_unknown_schema_extra_attribute_and_node_are_rejected(self) -> None:
        with self.assertRaises(ContentSchemaUnsupported):
            validate_content(full_document(), schema_version=99)
        invalid = full_document()
        invalid["unexpected"] = True
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(invalid, schema_version=1)

        invalid_v2 = full_document()
        invalid_v2["content"][0]["type"] = "script"
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(invalid_v2, schema_version=2)

    def test_v2_accepts_legacy_and_accessible_asset_nodes(self) -> None:
        validate_content(full_document(), schema_version=2)
        document = full_document()
        document["content"].append(
            {
                "type": "imageAsset",
                "attrs": {
                    "nodeId": "50000000-0000-4000-8000-000000000001",
                    "assetVersionId": "50000000-0000-4000-8000-000000000002",
                    "altText": "Gráfica de una función cuadrática",
                    "decorative": False,
                    "caption": "Figura 1",
                    "displaySize": "large",
                },
            }
        )
        validate_content(document, schema_version=2)

        missing_alt = full_document()
        missing_alt["content"].append(
            {
                "type": "imageAsset",
                "attrs": {
                    "nodeId": "50000000-0000-4000-8000-000000000003",
                    "assetVersionId": "50000000-0000-4000-8000-000000000004",
                    "altText": "",
                    "decorative": False,
                    "caption": "",
                    "displaySize": "large",
                },
            }
        )
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(missing_alt, schema_version=2)
        invalid = full_document()
        invalid["content"][0]["type"] = "script"
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(invalid, schema_version=1)

    def test_duplicate_ids_links_math_and_table_shape_are_rejected(self) -> None:
        duplicate = full_document()
        duplicate["content"][1]["attrs"]["nodeId"] = duplicate["content"][0]["attrs"][
            "nodeId"
        ]
        with self.assertRaises(ContentDuplicateNodeId):
            validate_content(duplicate, schema_version=1)

        unsafe_link = full_document()
        unsafe_link["content"][1]["content"][0]["marks"] = [
            {"type": "link", "attrs": {"href": "javascript:alert(1)"}}
        ]
        with self.assertRaises(ContentUnsafeLink):
            validate_content(unsafe_link, schema_version=1)

        unsafe_math = full_document()
        unsafe_math["content"][3]["attrs"]["latex"] = r"\require{texhtml}"
        with self.assertRaises(ContentUnsafeMath):
            validate_content(unsafe_math, schema_version=1)

        table = full_document()
        table["content"][-1]["content"][1]["content"].pop()
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(table, schema_version=1)

    def test_pathological_depth_fails_before_recursive_schema_validation(self) -> None:
        document = empty_document()
        current = document
        for _ in range(40):
            nested = {"type": "doc", "content": [current]}
            current = nested
        with self.assertRaises(ContentTooDeep):
            validate_content(current, schema_version=1)

    def test_invalid_ids_marks_attributes_languages_and_strings_are_rejected(
        self,
    ) -> None:
        invalid_id = full_document()
        invalid_id["content"][0]["attrs"]["nodeId"] = "not-a-uuid"
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(invalid_id, schema_version=1)

        unknown_mark = full_document()
        unknown_mark["content"][1]["content"][0]["marks"] = [{"type": "underline"}]
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(unknown_mark, schema_version=1)

        extra_attrs = full_document()
        extra_attrs["content"][0]["attrs"]["html"] = "<script>"
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(extra_attrs, schema_version=1)

        language = full_document()
        language["content"][4]["attrs"]["language"] = "bash"
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(language, schema_version=1)

        non_json = full_document()
        non_json["content"][0]["custom"] = {1, 2, 3}
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(non_json, schema_version=1)

    def test_node_text_and_serialized_size_limits_fail_before_schema(self) -> None:
        too_many = {
            "type": "doc",
            "payload": [
                {"type": "paragraph", "attrs": {"nodeId": str(index)}}
                for index in range(5001)
            ],
        }
        with self.assertRaises(ContentNodeLimitExceeded):
            validate_content(too_many, schema_version=1)

        too_much_text = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "attrs": {"nodeId": "30000000-0000-4000-8000-000000000001"},
                    "content": [{"type": "text", "text": "x" * 300_001}],
                }
            ],
        }
        with self.assertRaises(ContentTooLarge):
            validate_content(too_much_text, schema_version=1)

        over_megabyte = {"type": "doc", "padding": "x" * (1024 * 1024)}
        with self.assertRaises(ContentTooLarge):
            validate_content(over_megabyte, schema_version=1)

    def test_nested_semantic_structures_and_table_contract_are_rejected(self) -> None:
        nested_pedagogy = full_document()
        nested_pedagogy["content"][2]["content"].append(
            {
                "type": "pedagogicalBlock",
                "attrs": {
                    "nodeId": "40000000-0000-4000-8000-000000000001",
                    "kind": "example",
                },
                "content": [empty_document()["content"][0]],
            }
        )
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(nested_pedagogy, schema_version=1)

        nested_table = full_document()
        nested_table["content"][-1]["content"][1]["content"][0]["content"] = [
            full_document()["content"][-1]
        ]
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(nested_table, schema_version=1)

        no_caption = full_document()
        del no_caption["content"][-1]["attrs"]["caption"]
        with self.assertRaises(ContentSchemaInvalid):
            validate_content(no_caption, schema_version=1)
