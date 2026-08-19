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
        cls.korean = (THEME / "locale" / "ko.yml").read_text(encoding="utf-8")
        cls.forum_js = (THEME / "js" / "dist" / "forum.js").read_text(encoding="utf-8")
        cls.extend_php = (THEME / "extend.php").read_text(encoding="utf-8")
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
            ".UserHero",
            ".UserPage-content",
            ".SettingsPage",
            ".UserSecurityPage",
            ".NotificationGrid",
            ".AccessTokensList",
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
        self.assertIn("discussions_solutions_heading: 해결된 토론", self.korean)
        self.assertIn("해결된 토론 검색", self.korean)

    def test_accessibility_contract(self) -> None:
        self.assertIn(":focus-visible", self.less)
        self.assertIn("prefers-reduced-motion", self.less)

    def test_icon_font_fallback_contract(self) -> None:
        self.assertIn('font-family: "Segoe UI Symbol"', self.less)
        self.assertIn('.fa-search::before { content: "⌕"', self.less)
        self.assertIn('.fa-newspaper::before { content: "▤"', self.less)
        self.assertIn('.fa-ellipsis-v::before { content: "•••"', self.less)
        self.assertGreaterEqual(len(re.findall(r"min-height:\s*44px", self.less)), 3)
        self.assertGreaterEqual(contrast("#155eef", "#ffffff"), 4.5)
        self.assertGreaterEqual(contrast("#15253e", "#ffffff"), 12.0)
        self.assertGreaterEqual(contrast("#056038", "#d9f5e6"), 6.0)

    def test_responsive_and_korean_readability_contract(self) -> None:
        self.assertIn("@media (max-width: 767px)", self.less)
        self.assertIn("word-break: keep-all", self.less)
        self.assertIn('"Noto Sans KR"', self.less)
        self.assertIn("font-size: 16px", self.less)

    def test_tag_date_format_contract(self) -> None:
        self.assertIn("->js(__DIR__.'/js/dist/forum.js')", self.extend_php)
        self.assertIn("flarum.core.compat['forum/app']", self.forum_js)
        self.assertIn("module.exports = {}", self.forum_js)
        self.assertIn(".TagTile-lastPostedDiscussion time[datetime]", self.forum_js)
        self.assertIn("relativeDatePattern", self.forum_js)
        self.assertIn("matched[1].slice(-2) + '년 '", self.forum_js)
        self.assertIn("Number(matched[2]) + '월 '", self.forum_js)
        self.assertIn("Number(matched[3]) + '일'", self.forum_js)

    def test_compact_hero_and_navigation_width_contract(self) -> None:
        self.assertIn(".WelcomeHero .container", self.less)
        self.assertIn("font-size: 28px", self.less)
        self.assertIn("width: 240px", self.less)
        self.assertIn(".TagsPage-nav > ul", self.less)
        self.assertIn(".TagTiles", self.less)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr))", self.less)
        self.assertIn("gap: 18px", self.less)
        self.assertIn(".TagTile-lastPostedDiscussion::before", self.less)
        self.assertIn('content: "최근 토론"', self.less)
        self.assertIn("border-top: 4px solid var(--tag-bg)", self.less)
        self.assertIn(".TagsPage-content > .TagCloud", self.less)
        self.assertIn("grid-column-start: 1", self.less)
        self.assertIn("grid-column-end: -1", self.less)
        self.assertIn("grid-template-columns: repeat(4, minmax(0, 1fr))", self.less)
        self.assertIn('content: "보조 태그 · 제품과 기능별 세부 토론"', self.less)
        self.assertIn("content: attr(title)", self.less)
        self.assertIn("border-left: 4px solid var(--tag-bg)", self.less)
        self.assertIn("width: 100%", self.less)
        self.assertIn("article.Post.Post--bestAnswer > div", self.less)
        self.assertIn("✓ 선택된 해결 답변", self.less)
        self.assertIn("@media (min-width: 768px)", self.less)
        self.assertIn("white-space: nowrap", self.less)
        self.assertIn("padding: 11px 64px 11px 52px", self.less)
        self.assertIn("padding-top: 19px", self.less)
        self.assertIn("padding-bottom: 19px", self.less)
        self.assertIn("padding: 17px 15px", self.less)
        self.assertIn("border-bottom: 0", self.less)
        self.assertIn(".PostStream-item:not(:last-child)", self.less)
        self.assertIn(".DiscussionListItem-author", self.less)
        self.assertIn("margin-top: 1px !important", self.less)
        self.assertIn(".Post-actions", self.less)
        self.assertIn("right: 0", self.less)
        self.assertIn(".Post-actions > ul > li", self.less)
        self.assertIn("gap: 8px", self.less)
        self.assertIn("width: auto", self.less)
        self.assertIn("top: auto", self.less)
        self.assertIn("bottom: -48px", self.less)
        self.assertIn("bottom: -52px", self.less)
        self.assertIn(".item-like .Button-label::before", self.less)
        self.assertIn(".item-bestAnswer .Button-label::before", self.less)
        self.assertIn('content: "더 보기"', self.less)
        self.assertIn('content: "↶"', self.less)
        self.assertIn('[aria-disabled="true"]', self.less)
        self.assertIn(":has(.Header-secondary .item-logIn)", self.less)
        self.assertIn(".App--index > .App-navigation", self.less)
        self.assertIn("display: none !important", self.less)
        self.assertNotIn(".App--index > .App-navigation .Navigation-drawer", self.less)
        self.assertIn(".UserHero .UserCard-profile", self.less)
        self.assertIn(".UserPage .UserPage-nav", self.less)
        self.assertIn(".UserPage .UserPage-content", self.less)
        self.assertIn(".UserHero .UserCard-avatar", self.less)
        self.assertIn("position: absolute", self.less)
        self.assertIn("likes_link: 좋아요", self.korean)
        self.assertIn("media: 내 미디어", self.korean)
        self.assertIn("security_link: 보안", self.korean)
        self.assertIn("아직 작성한 게시물이 없습니다.", self.korean)
        self.assertIn("내 게시물이 해결 답변으로 선택되었을 때", self.korean)
        self.assertIn("참여한 토론에 해결 답변이 선택되었을 때", self.korean)
        self.assertIn("새 토큰", self.korean)
        self.assertIn("내가 속한 그룹이 게시물에서 언급되었을 때", self.korean)
        self.assertIn("토론의 마지막 게시물뿐 아니라 새 게시물이 등록될 때마다 알림", self.korean)
        self.assertIn("서식 편집기 사용", self.korean)
        self.assertIn("문단 사이의 빈 줄을 줄여서 표시", self.korean)
        self.assertIn("검색 정보 설정", self.korean)
        self.assertIn(".DiscussionListItem-controls", self.less)
        self.assertIn("z-index: 1080", self.less)
        self.assertIn("right: 58px", self.less)
        self.assertIn(".SettingsPage fieldset", self.less)
        self.assertIn(".UserSecurityPage fieldset", self.less)
        self.assertIn("overflow-x: auto", self.less)
        self.assertIn(".Composer.active", self.less)
        self.assertIn(".Modal .FormControl:focus-visible", self.less)
        self.assertIn(".Modal .Button--primary", self.less)
        self.assertIn(".Modal-close .Button:focus-visible", self.less)
        self.assertIn(".TagSelectionModal .TagsInput.FormControl.focus", self.less)
        self.assertIn(".TagSelectionModal-list > li.selected", self.less)
        self.assertIn("outline: none !important", self.less)
        self.assertIn("주 태그를 선택하세요", self.korean)
        self.assertIn("태그 필수 조건 무시", self.korean)
        self.assertIn("#console-nav-footer", self.less)
        self.assertIn("#footer-content .feedback-menu-left", self.less)
        self.assertIn('content: "⌂"', self.less)
        self.assertIn('content: "✎"', self.less)
        self.assertIn('content: "▤"', self.less)

    def test_rehearsal_is_staging_only_and_preserves_content(self) -> None:
        self.assertIn('APP_ROOT" == "/srv/techflow-flarum-staging/app"', self.rehearsal)
        self.assertIn("productionChanged", self.rehearsal)
        self.assertIn("compare_integrity", self.rehearsal)
        self.assertIn("uploads_sha256", self.rehearsal)
        self.assertIn("storage/locale", self.rehearsal)
        self.assertIn("core.forum.header.search_placeholder", self.rehearsal)
        self.assertIn("warm-korean-locale.php", self.rehearsal)
        self.assertIn('TECHFLOW_THEME_EXPECTED="$theme_expected"', self.rehearsal)
        locale_warmer = (THEME / "tools" / "warm-korean-locale.php").read_text(encoding="utf-8")
        self.assertIn("core.forum.user.security_link", locale_warmer)
        self.assertIn("flarum-likes.forum.user.likes_link", locale_warmer)
        self.assertIn("fof-upload.forum.buttons.media", locale_warmer)


if __name__ == "__main__":
    unittest.main()
