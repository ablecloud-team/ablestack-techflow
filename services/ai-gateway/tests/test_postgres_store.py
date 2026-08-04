from __future__ import annotations

from datetime import datetime, timezone
import unittest
from uuid import uuid4

from app.postgres_store import PostgresStore


class PostgresPayloadTest(unittest.TestCase):
    def test_returning_star_job_id_is_mapped(self) -> None:
        job_id = uuid4()
        source_id = uuid4()
        version_id = uuid4()
        now = datetime.now(timezone.utc)
        payload = PostgresStore._job_payload(
            {
                "id": job_id,
                "job_type": "INGESTION",
                "source_id": source_id,
                "source_version_id": version_id,
                "state": "PENDING",
                "failure_class": None,
                "error_code": None,
                "requested_by": "canary",
                "created_at": now,
                "updated_at": now,
            }
        )
        self.assertEqual(job_id, payload["jobId"])

    def test_aliased_job_id_is_also_supported(self) -> None:
        job_id = uuid4()
        now = datetime.now(timezone.utc)
        payload = PostgresStore._job_payload(
            {
                "job_id": job_id,
                "job_type": "DELETION",
                "source_id": uuid4(),
                "source_version_id": uuid4(),
                "state": "PENDING",
                "failure_class": None,
                "error_code": None,
                "requested_by": "system",
                "created_at": now,
                "updated_at": now,
            }
        )
        self.assertEqual(job_id, payload["jobId"])


if __name__ == "__main__":
    unittest.main()
