from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.community import FlarumClient, conversationalize_answer
from app.config import Settings
from app.conversation import (build_chat_question, build_conversation_question,
                              community_actionability_issues, community_result_advances)
from app.main import create_app
from app.platform_references import curated_platform_results
from app.provider import ComprehensiveResponsesResult, ContextChunk, MockResponsesAdapter
from app.store import MemoryStore
from app.support_intent import (capability_question, capability_result_complete,
                                capability_review_spec, prepare_capability_result)
from app.versioned_assist import feature_source_terms, format_public_answer, relevant_results


QUESTION = '''현재 ABLESTACK-VM으로 host 2대를 운영하고 있습니다.
아래 3가지 사항을 적용해도 문제가 없는지 확인 부탁드립니다.
Cube OS 일반계정으로 SSH 로그인 후 root 유저로 전환해도 상관없는지?
Cube OS(root 포함), Mold, WALL 웹 admin 패스워드를 주기적으로 변경해도 상관없는지?
Cube OS SSH 포트를 변경해도 상관없는지?'''
ACTIONS = [
    '[가능] CubeOS 일반 관리계정 로그인 후 허가된 root 전환이 가능합니다. 제품 내부 키 인증은 유지해야 합니다.',
    '[조건부 가능] CubeOS 일반계정과 root, Mold 및 Wall의 로컬 계정 비밀번호 변경은 가능합니다. '
    'Wall 외부 인증 구성은 해당 인증 정책을 따릅니다. 고객별 연동 영향은 기술지원센터 확인 대상입니다.',
    '[조건부 가능] CubeOS SSH 포트 변경 기능이 구현되어 있습니다. 서버와 내부 클라이언트 설정을 함께 반영합니다. '
    '설치 버전별 적용 절차는 ABLECLOUD 기술지원센터에 확인해 주세요.',
]


def result(actions=None, state='ANSWERED'):
    return {'state': state, 'report': {'state': state,
        'summary': 'CheckConsoleProxyLoadCommand는 콘솔 처리입니다.',
        'diagnoses': [{'title': '관련 없는 콘솔 진단'}],
        'recommendedActions': ACTIONS if actions is None else actions, 'unknowns': []}, 'citations': []}


class CapabilityReviewTests(unittest.TestCase):
    def test_three_questions_survive_html_number_loss_and_numbered_input(self):
        spec = capability_review_spec(QUESTION)
        self.assertEqual(3, len(spec.items))
        numbered = '\n'.join(f'{i}. {line}' for i, line in enumerate(spec.items, 1))
        self.assertEqual(spec.items, capability_review_spec(numbered).items)
        self.assertIn('Mold', spec.items[1])
        self.assertIn('SSH 포트', spec.items[2])

    def test_incidents_howto_and_incomplete_boundaries_are_not_capability_reviews(self):
        for question in ('CubeOS SSH 포트를 변경한 후 접속이 안됩니다. 영향이 있나요?',
                         'CubeOS SSH 포트 변경 방법을 알려주세요. 가능한가요?',
                         '아래 3가지 지원 여부 문의입니다.\nCubeOS SSH 변경이 가능한가요?',
                         'Ubuntu NTP 설정 방법을 알려 주세요.', '일반 VM 성능이 가능한가요?'):
            self.assertIsNone(capability_review_spec(question), question)

    def test_prompt_keeps_each_question_without_previous_incident_contamination(self):
        spec = capability_review_spec(QUESTION)
        for prompt in (capability_question(spec), build_chat_question([], QUESTION),
                       build_conversation_question('보안변경', [], {'question': QUESTION})):
            self.assertLessEqual(len(prompt.encode('utf-8')), 4000)
            self.assertIn('질문당 한 개', prompt)
            self.assertIn('기술지원센터', prompt)
            self.assertEqual(spec.items, capability_review_spec(prompt).items)

    def test_bounded_prompt_uses_compact_policy_without_truncating_any_question(self):
        spec = capability_review_spec(QUESTION)
        limit = len(capability_question(spec).encode('utf-8')) - 100
        prompt = capability_question(spec, limit=limit)
        self.assertLessEqual(len(prompt.encode('utf-8')), limit)
        self.assertEqual(spec.items, capability_review_spec(prompt).items)

    def test_public_answer_is_three_verdicts_not_incident_template(self):
        prepared = prepare_capability_result(result(), capability_review_spec(QUESTION))
        answer = format_public_answer(prepared)
        self.assertTrue(capability_result_complete(prepared))
        self.assertEqual(3, answer.count('### '))
        self.assertNotIn('ConsoleProxy', answer)
        self.assertNotIn('먼저 다음 해결', answer)
        self.assertNotIn('해결되지 않으면', answer)
        self.assertEqual(answer, conversationalize_answer(answer))
        self.assertEqual((), community_actionability_issues(prepared))
        self.assertTrue(community_result_advances(prepared, [{'role': 'ASSISTANT', 'content': answer}]))

    def test_invalid_or_partial_coverage_refers_every_question_without_fake_support(self):
        bad = [ACTIONS[:2], ['지원합니다.'] * 3,
               [ACTIONS[0], '[가능] CubeOS와 Mold 비밀번호 변경 가능.', ACTIONS[2]],
               [ACTIONS[0], ACTIONS[1], '[가능] sudo systemctl restart sshd'],
               [ACTIONS[0], ACTIONS[1], '[확인 불가] 장애 시각과 로그를 보내 주세요.']]
        for actions in bad:
            with self.subTest(actions=actions):
                prepared = prepare_capability_result(result(actions), capability_review_spec(QUESTION))
                self.assertEqual('ABSTAINED', prepared['state'])
                self.assertEqual('ABSTAINED', prepared['report']['state'])
                self.assertEqual(3, len(prepared['capabilityAnswers']))
                self.assertTrue(capability_result_complete(prepared))
                answer = format_public_answer(prepared)
                self.assertEqual(3, answer.count('**확인 불가**'))
                self.assertNotIn('로그를 보내', answer)
                self.assertIn('기술지원센터', answer)

    def test_unknown_evidence_uses_center_and_provider_failure_is_not_hidden(self):
        unknown = prepare_capability_result(result([], 'ABSTAINED'), capability_review_spec(QUESTION))
        self.assertTrue(capability_result_complete(unknown))
        failed = result([], 'FAILED')
        self.assertIs(failed, prepare_capability_result(failed, capability_review_spec(QUESTION)))
        self.assertFalse(capability_result_complete(failed))

    def test_community_api_preserves_provider_failure_without_publication(self):
        from app.responses import ResponsesProviderError
        adapter = MockResponsesAdapter()
        flarum = FlarumClient('http://forum', 'https://forum', None, True)
        client = TestClient(create_app(Settings(community_auto_publish_enabled=True, community_publish_enabled=True,
            flarum_api_key_file='/unused/key', flarum_assistant_user_id_file='/unused/assistant',
            flarum_solution_selector_user_id_file='/unused/selector'),
            MemoryStore(), responses_adapter=adapter, flarum_client_instance=flarum))
        chunk = ContextChunk('security', 'D0', 'synthetic', 'main', '0'*40, 'security_patch.sh', 'Test evidence')
        with patch.object(flarum, 'post_is_visible', return_value=True), \
             patch.object(flarum, 'publish_assistant_reply') as publication, \
             patch('app.main.context_from_results', return_value=(chunk,)), \
             patch.object(adapter, 'generate_comprehensive', side_effect=ResponsesProviderError(
                 'PROVIDER_UNAVAILABLE', 'RETRYABLE', profile_id='OPENAI_RAG_ESCALATION_V1', requested_model_id='mock',
                 latency_ms=1, provider_called=True)):
            response = client.post('/v1/community/cases', json={
                'discussionId':'210', 'discussionUrl':'https://community.ablecloud.io/d/210',
                'authorId':'99', 'postAuthorId':'99', 'postId':'593', 'postNumber':1,
                'title':'지원 여부', 'question':QUESTION}, headers={
                    'X-Correlation-Id':'capability-failure', 'Idempotency-Key':'capability-failure'})
            self.assertEqual(503, response.status_code, response.text)
            publication.assert_not_called()

    def test_unknown_verdict_adds_center_and_tampered_count_cannot_bypass_validation(self):
        prepared = prepare_capability_result(result([*ACTIONS[:2], '[확인 불가] 설치 버전 적용 여부는 미확인입니다.']),
                                             capability_review_spec(QUESTION))
        self.assertIn('기술지원센터', prepared['capabilityAnswers'][2]['answer'])
        prepared['capabilityAnswers'].pop()
        self.assertFalse(capability_result_complete(prepared))

    def test_korean_particles_do_not_turn_complete_product_answers_into_referrals(self):
        actions=[ACTIONS[0], '[조건부 가능] CubeOS의 계정 암호 변경은 가능합니다. Mold는 사용자 암호 변경을 지원하고, '
                 'Wall의 로컬 암호도 변경 가능합니다. 외부 인증은 별도입니다.', ACTIONS[2]]
        prepared=prepare_capability_result(result(actions),capability_review_spec(QUESTION))
        self.assertEqual('ANSWERED',prepared['state'])
        self.assertFalse(prepared.get('capabilityReferralFallback',False))
        self.assertTrue(capability_result_complete(prepared))

    def test_product_matching_accepts_korean_particles_but_not_other_ascii_words(self):
        from app.support_intent import _products
        self.assertEqual({'CubeOS','Mold','Wall'},_products('Cube OS계정과 Mold는 Wall의 구성과 다릅니다.'))
        self.assertEqual(set(),_products('CubeOSX MoldX Firewall SMALLWALL mold_account'))

    def test_security_retrieval_excludes_console_and_includes_pinned_feature_sources(self):
        anchors = feature_source_terms(QUESTION)
        self.assertIn('security_patch.py', anchors)
        self.assertIn('ChangeUserPassword', anchors)
        self.assertNotIn('createConsoleEndpoint', anchors)
        refs = curated_platform_results(QUESTION)
        selected = relevant_results(QUESTION, [*refs,
            {'path': 'ConsoleAccessManagerImpl.java', 'content': 'Mold console createConsoleEndpoint'},
            {'path': 'CheckConsoleProxyLoadCommand.java', 'content': 'Mold VNC console'}])
        paths = '\n'.join(row['path'] for row in selected)
        for path in ('security_patch.sh', 'security_patch.py', 'UpdateUserCmd.java', 'pkg/api/user.go'):
            self.assertIn(path, paths)
        self.assertNotIn('ConsoleAccessManager', paths)
        self.assertNotIn('ConsoleProxy', paths)
        self.assertIn('createconsoleendpoint', feature_source_terms('Mold 콘솔 연결이 안됩니다.'))

    def test_community_api_uses_all_items_and_publishes_once(self):
        adapter = MockResponsesAdapter()
        flarum = FlarumClient('http://forum', 'https://forum', None, True)
        client = TestClient(create_app(Settings(community_auto_publish_enabled=True, community_publish_enabled=True,
            flarum_api_key_file='/unused/key', flarum_assistant_user_id_file='/unused/assistant',
            flarum_solution_selector_user_id_file='/unused/selector'), MemoryStore(),
            responses_adapter=adapter, flarum_client_instance=flarum))
        chunk = ContextChunk('security-210', 'D0', 'synthetic', 'main', '0'*40,
                             'security_patch.sh', 'Synthetic feature evidence for testing only')
        generated = ComprehensiveResponsesResult(report=result()['report'], citations_used=(),
            requested_model_id='mock', returned_model_id='mock', request_id='mock-210', response_id='mock-210')
        payload = {'discussionId': '210', 'discussionUrl': 'https://community.ablecloud.io/d/210',
                   'authorId': '99', 'postAuthorId': '99', 'postId': '593', 'postNumber': 1,
                   'title': '보안 변경 영향', 'question': QUESTION}
        headers = {'X-Correlation-Id': 'capability-210-test', 'Idempotency-Key': 'capability-210-test'}
        with patch.object(flarum, 'post_is_visible', return_value=True), \
             patch.object(flarum, 'visible_post_ids', return_value={'593', '594'}), \
             patch.object(flarum, 'publish_assistant_reply', return_value={
                 'postId': '594', 'postUrl': 'https://community.ablecloud.io/d/210/2'}) as publication, \
             patch('app.main.context_from_results', return_value=(chunk,)), \
             patch.object(adapter, 'generate_comprehensive', return_value=generated) as provider, \
             patch('app.main.sync_account_hardening_result', side_effect=AssertionError('single-topic shortcut')):
            response = client.post('/v1/community/cases', json=payload, headers=headers)
            self.assertEqual(201, response.status_code, response.text)
            self.assertEqual('PUBLISHED', response.json()['data']['state'])
            self.assertEqual(3, response.json()['data']['draftAnswer'].count('### '))
            self.assertIn('[기능·지원 검토]', provider.call_args.args[0].question)
            again = client.post('/v1/community/cases', json=payload, headers=headers)
            self.assertEqual('594', again.json()['data']['publishedPostId'])
            publication.assert_called_once()
            provider.assert_called_once()


if __name__ == '__main__':
    unittest.main()
