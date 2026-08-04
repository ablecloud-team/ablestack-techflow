from __future__ import annotations

import unittest

from tools.ai_gateway.validate_issue_41 import EXPECTED_OPERATIONS, EXPECTED_TABLES, validate


class Issue41ValidatorTest(unittest.TestCase):
    def test_operation_count(self) -> None:
        self.assertEqual(11, len(EXPECTED_OPERATIONS))

    def test_table_count(self) -> None:
        self.assertEqual(15, len(EXPECTED_TABLES))

    def test_repository_assets_are_valid(self) -> None:
        self.assertEqual([], validate())


if __name__ == "__main__":
    unittest.main()
