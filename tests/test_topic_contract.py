"""No-database smoke test for taxonomy and LLM batch-result validation."""

import unittest

from reporting.enrichment.topic_contract import validate_taxonomy_payload
from reporting.enrichment.topic_result_validator import validate_topic_batch_results


class TopicContractTests(unittest.TestCase):
    def setUp(self):
        self.taxonomy = validate_taxonomy_payload(
            {
                "taxonomy_version": "demo_social_topic_v1",
                "taxonomy_name": "Demo Social Topics",
                "description": "Unit-test taxonomy.",
                "topics": [
                    {
                        "topic_id": "service_praise",
                        "label": "Apresiasi Layanan",
                        "description": "Pujian terhadap layanan.",
                    },
                    {
                        "topic_id": "other_emerging_topic",
                        "label": "Topik Baru / Perlu Review",
                        "description": "Belum cocok taxonomy.",
                    },
                    {
                        "topic_id": "not_relevant",
                        "label": "Tidak Relevan",
                        "description": "Di luar scope.",
                    },
                ],
            }
        )

    def test_full_batch_result_is_normalized(self):
        batch = {
            "post_refs": [
                {
                    "canonical_post_id": 1,
                    "canonical_key": "url:https://example.com/a",
                    "content_hash": "a" * 64,
                }
            ]
        }
        results = [
            {
                "canonical_key": "url:https://example.com/a",
                "content_hash": "a" * 64,
                "primary_topic_id": "service_praise",
                "classification_status": "classified",
                "confidence": "high",
            }
        ]
        normalized = validate_topic_batch_results(
            batch=batch,
            taxonomy=self.taxonomy,
            results=results,
        )
        self.assertEqual(normalized[0]["primary_topic_label"], "Apresiasi Layanan")

    def test_rejects_topic_not_in_taxonomy(self):
        batch = {
            "post_refs": [
                {
                    "canonical_post_id": 1,
                    "canonical_key": "url:https://example.com/a",
                    "content_hash": "a" * 64,
                }
            ]
        }
        with self.assertRaises(ValueError):
            validate_topic_batch_results(
                batch=batch,
                taxonomy=self.taxonomy,
                results=[
                    {
                        "canonical_key": "url:https://example.com/a",
                        "content_hash": "a" * 64,
                        "primary_topic_id": "invented_topic",
                        "classification_status": "classified",
                        "confidence": "high",
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()
