from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
THEME = ROOT / "deploy" / "flarum" / "extensions" / "ablecloud-community-theme"


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class CommunityThemeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.composer = json.loads((THEME / "composer.json").read_text(encoding="utf-8"))
        cls.less = (THEME / "resources" / "less" / "forum.less").read_text(encoding="utf-8")
        cls.rehearsal = (ROOT / "deploy" / "flarum" / "rehearse-community-theme.sh").read_text(encoding="utf-8")

    def test_is_isolated_flarum_extension(self) -> None:
        self.assertEqual(self.composer["type"], "flarum-extension")
        self.assertEqual(self.composer["require"]["flarum/core"], "^1.8")
        self.assertNotIn("vendor/", self.rehearsal)
        self.assertIn("extension:disable", self.rehearsal)

    def test_required_screen_contracts(self) -> None:
        selectors = (
            ".WelcomeHero",
            ".DiscussionListItem",
            ".DiscussionHero",
            ".Post-body",
            ".Composer",
            ".FoFUpload-uploadButton",
            ".Search-input input",
            ".Modal-content",
        )
        for selector in selectors:
            with self.subTest(selector=selector):
                self.assertIn(selector, self.less)

    def test_ai_states_are_distinct(self) -> None:
        for state in ("assistant", "knowledge-base", "needs-information"):
            self.assertIn(f"TechFlowPost--{state}", self.less)
        self.assertIn("/u/TechFlow-Assistant", self.less)
        self.assertIn('content: "최종 해결 가이드"', self.less)

    def test_korean_best_answer_labels(self) -> None:
        for text in ("해결됨", "해결 답변으로 선택", "해결 답변 선택 취소", "해결된 답변"):
            self.assertIn(text, self.less)

    def test_accessibility_contract(self) -> None:
        self.assertIn(":focus-visible", self.less)
        self.assertIn("prefers-reduced-motion", self.less)
        self.assertGreaterEqual(len(re.findall(r"min-height:\s*44px", self.less)), 3)
        self.assertGreaterEqual(contrast("#155eef", "#ffffff"), 4.5)
        self.assertGreaterEqual(contrast("#15253e", "#ffffff"), 12.0)
        self.assertGreaterEqual(contrast("#056038", "#d9f5e6"), 6.0)

    def test_responsive_and_korean_readability_contract(self) -> None:
        self.assertIn("@media (max-width: 767px)", self.less)
        self.assertIn("word-break: keep-all", self.less)
        self.assertIn('"Noto Sans KR"', self.less)
        self.assertIn("font-size: 16px", self.less)

    def test_rehearsal_is_staging_only_and_preserves_content(self) -> None:
        self.assertIn('APP_ROOT" == "/srv/techflow-flarum-staging/app"', self.rehearsal)
        self.assertIn("productionChanged", self.rehearsal)
        self.assertIn("compare_integrity", self.rehearsal)
        self.assertIn("uploads_sha256", self.rehearsal)
        self.assertIn("storage/locale", self.rehearsal)
        self.assertIn("core.forum.header.search_placeholder", self.rehearsal)
        self.assertIn("warm-korean-locale.php", self.rehearsal)


if __name__ == "__main__":
    unittest.main()
