from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.community import FlarumClient
from app.config import Settings
from app.conversation import build_knowledge_base_question, is_confirmed_resolution_report
from app.main import create_app
from app.provider import ComprehensiveResponsesResult, ProviderContractError
from app.store import MemoryStore


class LateKnowledgeRefreshTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.store = MemoryStore()
        first = {'discussionId': '199', 'discussionUrl': 'https://community.ablecloud.io/d/199',
                 'authorId': '68', 'title': 'GFS 스토리지 구성 오류', 'question': 'GFS 구성이 진행 중에서 멈춥니다.',
                 'postId': '540', 'postNumber': 1, 'postAuthorId': '68', 'artifactIds': []}
        self.case = self.store.create_community_case(first, {'draftAnswer': '용량 확인', 'answerState': 'ANSWERED'}, 'first', 'first')
        self.store.mark_community_auto_published(self.case['caseId'], '용량 확인', {'postId': '549', 'postUrl': 'https://forum/d/199/6'}, 'pub')
        self.store.record_community_turn({**first, 'postId': '548', 'postNumber': 5, 'question': '스토리지를 500M로 설정했습니다.'}, '548', '548')
        self.store.sync_community_resolution({**first, 'bestAnswerPostId': '548', 'bestAnswerUserId': '68'}, 'resolved', 'resolved')
        self.store.mark_community_knowledge_published(self.case['caseId'], '이전 용량 가설', {'postId': '550', 'postUrl': 'https://forum/d/199/7'}, 'kb')
        self.store.record_community_turn({**first, 'postId': '550', 'postNumber': 7, 'postAuthorId': '40',
                                          'turnRole': 'ASSISTANT', 'question': '이전 용량 가설'}, '550', '550')
        self.store.mark_community_knowledge_solution_selected(self.case['caseId'], {'postId': '550', 'selectedByUserId': '1'}, 'selected')
        self.source = {'postId': '559', 'postNumber': 8, 'authorUserId': '101',
                       'content': '원인은 멀티패스 미설정이었습니다. 멀티패스 설정후 구성이 되었습니다.'}
        self.flarum = FlarumClient('http://forum', 'https://forum', None, True)
        self.stack.enter_context(patch.object(self.flarum, 'post_is_visible', return_value=True))
        self.stack.enter_context(patch.object(self.flarum, '_assistant_user_id', return_value='40'))
        self.details = self.stack.enter_context(patch.object(self.flarum, 'visible_post_details', side_effect=self.post_details))
        self.selected = self.stack.enter_context(patch.object(self.flarum, 'knowledge_base_is_selected', return_value=True))
        self.stack.enter_context(patch.object(self.flarum, 'visible_post_ids', return_value={'540', '548', '550', '559', '560'}))
        self.update = self.stack.enter_context(patch.object(self.flarum, 'update_assistant_reply', return_value={'postId': '550', 'postUrl': 'https://forum/d/199/7'}))
        self.publish = self.stack.enter_context(patch.object(self.flarum, 'publish_assistant_reply'))
        self.select = self.stack.enter_context(patch.object(self.flarum, 'select_solution', return_value={'postId': '550', 'selectedByUserId': '1'}))
        self.provider = Mock()
        self.provider.generate_comprehensive.return_value = ComprehensiveResponsesResult(
            report={'state': 'ANSWERED', 'summary': '멀티패스 설정 후 구성됐다는 보고',
                    'observedFacts': ['GFS 구성 대기 현상'], 'diagnoses': ['후속 참여자는 멀티패스 미설정을 원인으로 보고했습니다.'],
                    'recommendedActions': ['해당 환경에서 멀티패스 설정 후 구성이 완료됐습니다.'], 'unknowns': []},
            citations_used=(), requested_model_id='mock', returned_model_id='mock', request_id='mock', response_id='mock')
        self.stack.enter_context(patch.object(self.store, 'retrieve', return_value={'results': [{
            'chunkId': 'chunk-gfs', 'sourceVersionId': '00000000-0000-0000-0000-000000000001',
            'sourceProfileId': 'SHARED_DOCS', 'repository': 'ablecloud-team/ablestack-docs', 'branch': 'master',
            'commit': 'a' * 40, 'path': 'gfs_manage.py', 'startLine': 1, 'endLine': 3,
            'sourceKind': 'DOCUMENTATION', 'content': '멀티패스 설정후 구성이 되었습니다. GFS 스토리지 구성 오류와 500M 용량 점검'}]}))
        settings = Settings(community_auto_publish_enabled=True, community_publish_enabled=True,
                            flarum_api_key_file='/unused/key', flarum_assistant_user_id_file='/unused/assistant',
                            flarum_solution_selector_user_id_file='/unused/selector')
        self.client = TestClient(create_app(settings, self.store, responses_adapter=self.provider, flarum_client_instance=self.flarum))
        self.event = {**first, 'postId': '559', 'postNumber': 8, 'postAuthorId': '101', 'turnRole': 'STAFF',
                      'responseRequested': False, 'responseReason': 'STAFF_RECORDED', 'question': self.source['content']}

    def post_details(self, discussion_id, post_id):
        self.assertEqual('199', discussion_id)
        if post_id == '550':
            return {'postId': '550', 'postNumber': 7, 'authorUserId': '40', 'content': '기존 KB'}
        return {**self.source, 'postId': post_id}

    def send(self, event=None):
        return self.client.post('/v1/community/cases', json=event or self.event,
                                headers={'X-Correlation-Id': 'late-kb-test', 'Idempotency-Key': 'late-kb-test-post559'})

    def test_case199_late_staff_result_updates_same_kb_and_keeps_original_selection_provenance(self):
        response = self.send()
        self.assertEqual(201, response.status_code, response.text)
        case = response.json()['data']
        self.assertEqual('550', case['knowledgeBasePostId'])
        self.assertEqual('548', case['resolvedPostId'])
        self.assertEqual('68', case['resolvedByUserId'])
        self.assertEqual('559', case['knowledgeBaseRevision']['postId'])
        self.assertIsNone(case['knowledgeBaseRefresh'])
        self.assertEqual(2, case['knowledgeBaseVersion'])
        self.assertIn('멀티패스', case['knowledgeBaseAnswer'])
        self.assertIn('[선택 이후 추가된 사람의 해결 보고]', self.provider.generate_comprehensive.call_args.args[0].question)
        self.assertIn('담당자', self.provider.generate_comprehensive.call_args.args[0].question)
        self.assertNotIn('이전 용량 가설', self.provider.generate_comprehensive.call_args.args[0].question)
        self.update.assert_called_once()
        self.publish.assert_not_called()
        self.select.assert_called_once_with('199', '550')
        self.assertEqual(case['knowledgeBaseAnswer'], next(t['content'] for t in self.store.list_community_turns('199') if t['sourcePostId'] == '550'))
        again = self.send()
        self.assertEqual(2, again.json()['data']['knowledgeBaseVersion'])
        self.assertEqual(1, self.provider.generate_comprehensive.call_count)

    def test_requester_success_updates_kb_without_reopening(self):
        self.source['authorUserId'] = '68'
        response = self.send({**self.event, 'turnRole': 'REQUESTER', 'responseRequested': True,
                              'responseReason': 'REQUESTER_AUTO', 'postAuthorId': '68'})
        self.assertEqual(201, response.status_code, response.text)
        self.assertEqual('RESOLVED', response.json()['data']['conversationState'])
        self.publish.assert_not_called()

    def test_internal_refresh_flags_cannot_be_supplied_by_api_caller(self):
        response = self.send({**self.event, 'preserveResolution': True,
                              'knowledgeBaseRefresh': {'postId': '559'}})
        self.assertEqual(422, response.status_code)
        self.update.assert_not_called()

    def test_new_human_solution_selection_also_reuses_existing_kb(self):
        self.store.record_community_turn(self.event, 'ingest-new-solution', 'ingest')
        response = self.send({**self.event, 'resolutionOnly': True, 'responseRequested': False,
                              'bestAnswerPostId': '559', 'bestAnswerUserId': '68'})
        self.assertEqual(201, response.status_code, response.text)
        case = response.json()['data']
        self.assertEqual('550', case['knowledgeBasePostId'])
        self.assertEqual('559', case['resolvedPostId'])
        self.assertEqual('559', case['knowledgeBaseSourcePostId'])
        self.assertEqual(2, case['knowledgeBaseVersion'])
        self.update.assert_called_once()
        self.publish.assert_not_called()
        self.select.assert_called_once_with('199', '550')

    def test_previously_recorded_source_is_refreshed_from_authoritative_content(self):
        self.store.record_community_turn({**self.event, 'turnRole': 'ASSISTANT', 'postAuthorId': '40',
                                         'question': '이전 내용'}, 'stale-event', 'stale')
        response = self.send()
        self.assertEqual(201, response.status_code, response.text)
        turn = next(t for t in self.store.list_community_turns('199') if t['sourcePostId'] == '559')
        self.assertEqual('STAFF', turn['role'])
        self.assertEqual('101', turn['authorUserId'])
        self.assertEqual(self.source['content'], turn['content'])



    def test_provider_failure_keeps_old_kb_and_retry_resumes(self):
        self.provider.generate_comprehensive.side_effect = ProviderContractError('unavailable')
        response = self.send()
        self.assertEqual(503, response.status_code)
        case = self.store.get_community_case_by_discussion('199')
        self.assertTrue(case['knowledgeBaseRefresh'])
        self.assertEqual('이전 용량 가설', case['knowledgeBaseAnswer'])
        self.update.assert_not_called()
        self.provider.generate_comprehensive.side_effect = None
        response = self.send()
        self.assertEqual(201, response.status_code, response.text)
        self.assertIsNone(response.json()['data']['knowledgeBaseRefresh'])

    def test_selection_failure_retries_only_selection(self):
        self.select.side_effect = RuntimeError('unavailable')
        self.assertEqual(503, self.send().status_code)
        self.assertTrue(self.store.get_community_case_by_discussion('199')['knowledgeBaseRefresh'])
        self.select.side_effect = None
        self.assertEqual(201, self.send().status_code)
        self.assertEqual(1, self.provider.generate_comprehensive.call_count)
        self.assertEqual(1, self.update.call_count)

    def test_pending_source_edited_to_unresolved_cancels_refresh(self):
        self.provider.generate_comprehensive.side_effect = ProviderContractError('offline')
        self.assertEqual(503, self.send().status_code)
        self.source['content'] = '아직 해결되지 않았습니다.'
        self.assertEqual(201, self.send().status_code)
        self.assertIsNone(self.store.get_community_case_by_discussion('199')['knowledgeBaseRefresh'])
        self.update.assert_not_called()

    def test_publication_failure_does_not_advance_committed_revision(self):
        self.update.side_effect = RuntimeError('offline')
        self.assertEqual(503, self.send().status_code)
        case = self.store.get_community_case_by_discussion('199')
        self.assertEqual(1, case['knowledgeBaseVersion'])
        self.assertFalse(case.get('knowledgeBaseRevision'))
        self.assertTrue(case['knowledgeBaseRefresh'])
        self.select.assert_not_called()
        self.update.side_effect = None
        self.assertEqual(201, self.send().status_code)

    def test_newer_committed_revision_cannot_be_overwritten_by_older_delivery(self):
        self.source.update(postId='560', postNumber=9)
        self.assertEqual(201, self.send({**self.event, 'postId': '560', 'postNumber': 9}).status_code)
        self.source.update(postId='559', postNumber=8)
        response = self.send()
        self.assertEqual(201, response.status_code)
        self.assertEqual('560', response.json()['data']['knowledgeBaseRevision']['postId'])
        self.assertEqual(1, self.update.call_count)

    def test_new_unresolved_requester_turn_reopens_without_leaving_refresh_pending(self):
        self.provider.generate_comprehensive.side_effect = ProviderContractError('offline')
        self.assertEqual(503, self.send().status_code)
        first = {**self.event, 'postId': '560', 'postNumber': 9, 'turnRole': 'REQUESTER', 'postAuthorId': '68',
                 'question': '여전히 문제가 발생합니다.', 'knowledgeBaseRefresh': None}
        case = self.store.create_community_case(first, {'draftAnswer': '진단을 이어갑니다.', 'answerState': 'ANSWERED'},
                                               'new-unresolved', 'new-unresolved')
        self.assertNotEqual('RESOLVED', case['conversationState'])
        self.assertIsNone(case.get('knowledgeBaseRefresh'))
        self.assertIsNone(case['knowledgeBasePostId'])

    def test_question_suggestion_unresolved_report_and_ai_source_do_not_refresh(self):
        for content in ('멀티패스 설정하면 구성이 되나요?', '멀티패스를 설정해 보세요.',
                        '설정 후에도 여전히 실패합니다.', '> 설정 후 문제가 해결되었습니다.'):
            self.source['content'] = content
            self.send()
        self.source.update(content='설정 후 문제가 해결되었습니다.', authorUserId='40')
        self.send()
        self.update.assert_not_called()
        self.publish.assert_not_called()

    def test_withdrawn_source_cancels_pending_without_writing(self):
        self.provider.generate_comprehensive.side_effect = ProviderContractError('unavailable')
        self.assertEqual(503, self.send().status_code)
        with patch.object(self.flarum, 'post_is_visible', return_value=False):
            response = self.send()
        self.assertTrue(response.json()['data']['cancelled'])
        self.assertIsNone(self.store.get_community_case_by_discussion('199')['knowledgeBaseRefresh'])
        self.update.assert_not_called()

    def test_unset_live_solution_and_changed_source_during_generation_prevent_write(self):
        self.selected.return_value = False
        self.send()
        self.update.assert_not_called()
        self.selected.return_value = True
        def generate(_):
            result = self.provider.generate_comprehensive.return_value
            self.source['content'] += ' (수정됨)'
            return result
        self.provider.generate_comprehensive.side_effect = generate
        self.assertEqual(503, self.send().status_code)
        self.update.assert_not_called()

    def test_simultaneous_duplicate_delivery_refreshes_once(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: self.send(), range(2)))
        self.assertTrue(all(r.status_code == 201 for r in responses), [r.text for r in responses])
        self.assertEqual(1, self.update.call_count)
        self.assertEqual(1, self.provider.generate_comprehensive.call_count)

    def test_affirmative_outcome_and_bounded_pinned_source(self):
        self.assertTrue(is_confirmed_resolution_report('멀티패스 설정후 구성이 되었습니다.'))
        for text in ('구성이 되었습니다?', '설정하면 구성이 되었습니다.', '[quote]문제가 해결되었습니다.[/quote]',
                     '정상 동작을 확인하십시오.', '<blockquote>문제가 해결되었습니다.</blockquote>',
                     '문제가 해결되었습니다. 하지만 아직 정상적으로 동작하지 않습니다.'):
            self.assertFalse(is_confirmed_resolution_report(text), text)
        turns = [{'sourcePostId': '548', 'postNumber': 5, 'role': 'REQUESTER', 'content': '500M 용량'},
                 *[{'sourcePostId': str(n), 'postNumber': n, 'role': 'ASSISTANT', 'content': '이전 추측' * 900} for n in range(10, 25)],
                 {'sourcePostId': '559', 'postNumber': 99, 'role': 'STAFF', 'content': self.source['content']}]
        prompt = build_knowledge_base_question('GFS 구성 오류', turns, '548', update_post_id='559')
        self.assertLessEqual(len(prompt), 16000)
        self.assertIn('멀티패스 설정후 구성이 되었습니다', prompt)


class FlarumRefreshBoundaryTests(unittest.TestCase):
    def test_visible_source_details_check_post_discussion_and_approval(self):
        client = FlarumClient('http://forum', 'https://forum', None, True)
        item = {'id': '559', 'attributes': {'contentType': 'comment', 'content': ' 해결되었습니다. ', 'number': 8},
                'relationships': {'discussion': {'data': {'id': '199'}}, 'user': {'data': {'id': '101'}}}}
        with patch.object(client, '_request', return_value={'data': item}) as request:
            self.assertEqual('101', client.visible_post_details('199', '559')['authorUserId'])
            request.assert_called_with('/api/posts/559?include=discussion', as_solution_selector=True)
            with self.assertRaises(RuntimeError):
                client.visible_post_details('200', '559')
            item['attributes']['isApproved'] = False
            with self.assertRaises(RuntimeError):
                client.visible_post_details('199', '559')

    def test_live_selection_requires_exact_visible_discussion_and_kb(self):
        client = FlarumClient('http://forum', 'https://forum', None, True)
        item = {'id': '199', 'attributes': {}, 'relationships': {'bestAnswerPost': {'data': {'id': '550'}}}}
        with patch.object(client, '_request', return_value={'data': item}):
            self.assertTrue(client.knowledge_base_is_selected('199', '550'))
            self.assertFalse(client.knowledge_base_is_selected('199', '559'))
            self.assertFalse(client.knowledge_base_is_selected('200', '550'))
            item['attributes']['isHidden'] = True
            self.assertFalse(client.knowledge_base_is_selected('199', '550'))


if __name__ == '__main__':
    unittest.main()
