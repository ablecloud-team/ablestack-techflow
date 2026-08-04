from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
UP = (ROOT / "migrations" / "0001_schema_up.sql").read_text(encoding="utf-8")
DOWN = (ROOT / "migrations" / "0001_schema_down.sql").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "migrations" / "0000_extensions_roles_up.sql").read_text(encoding="utf-8")


class MigrationContractTest(unittest.TestCase):
    def test_exactly_fifteen_tables(self) -> None:
        tables = re.findall(r"(?im)^CREATE TABLE\s+(rag_[a-z_]+)", UP)
        self.assertEqual(15, len(tables))
        self.assertEqual(15, len(set(tables)))

    def test_down_drops_all_fifteen_tables(self) -> None:
        created = set(re.findall(r"(?im)^CREATE TABLE\s+(rag_[a-z_]+)", UP))
        dropped = set(re.findall(r"(?im)^DROP TABLE IF EXISTS\s+(rag_[a-z_]+)", DOWN))
        self.assertEqual(created, dropped)

    def test_required_extensions(self) -> None:
        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector", BOOTSTRAP)
        self.assertIn("CREATE EXTENSION IF NOT EXISTS pg_trgm", BOOTSTRAP)

    def test_three_group_roles_are_no_login(self) -> None:
        for role in ("techflow_rag_migrator", "techflow_rag_app", "techflow_rag_source_fetcher"):
            self.assertRegex(BOOTSTRAP, rf"CREATE ROLE {role} NOLOGIN")

    def test_provider_call_has_safe_metadata(self) -> None:
        block = UP.split("CREATE TABLE rag_provider_call", 1)[1].split(");", 1)[0].lower()
        for field in ("requested_model_id", "returned_model_id", "provider_request_id", "latency_ms", "error_code"):
            self.assertIn(field, block)
        for forbidden in ("prompt ", "response ", "authorization", "api_key", "credential", "content "):
            self.assertNotIn(forbidden, block)

    def test_embedding_dimension_is_3072(self) -> None:
        self.assertIn("embedding vector(3072) NOT NULL", UP)
        self.assertIn("'OPENAI_EMBEDDING_V1'", UP)

    def test_d0_checks_exist_on_source_chunk_and_case(self) -> None:
        self.assertGreaterEqual(UP.count("CHECK (classification = 'D0')"), 3)

    def test_idempotency_is_persisted_on_mutations(self) -> None:
        self.assertGreaterEqual(UP.count("idempotency_key varchar(128)"), 5)

    def test_activepieces_role_is_absent(self) -> None:
        self.assertNotIn("activepieces", (UP + BOOTSTRAP).lower())

    def test_public_table_privileges_are_revoked(self) -> None:
        self.assertIn("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC", UP)


if __name__ == "__main__":
    unittest.main()
