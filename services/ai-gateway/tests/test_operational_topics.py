import unittest
from unittest.mock import patch
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from app.store import MemoryStore
from app.community import FlarumClient
from app.provider import ComprehensiveResponsesResult, ContextChunk, MockResponsesAdapter
from app.operational_topics import current_operation_text, nonincident_operation, operation_topics
from app.versioned_assist import feature_source_terms, relevant_results, select_context_results, format_public_answer
from app.platform_references import curated_platform_results

CURRENT = ('TechFlow-Assistant\n부하분산이 호스트 간 VM 분산이라면 라이브 마이그레이션을 사용하십시오. '
           '현재 CCVM command execution test failed.\n'
           '위와 같은 의미가 아니라 트래픽이 들어올때 nginx같은 웹 서비스상의 부하분산 말이야\n'
           '그리고 HCI의 CUBE의 OS 버전이 계속 업그레이드 되는데 자동 업데이트 하는 부분도 잇을까?')


class OperationalTopicTests(unittest.TestCase):
    def test_community_api_routes_new_operations_through_sources_and_publishes_once(self):
        adapter=MockResponsesAdapter()
        flarum=FlarumClient('http://forum','https://forum',None,True)
        client=TestClient(create_app(Settings(community_auto_publish_enabled=True,community_publish_enabled=True,
            flarum_api_key_file='/unused/key',flarum_assistant_user_id_file='/unused/assistant',
            flarum_solution_selector_user_id_file='/unused/selector'),MemoryStore(),responses_adapter=adapter,
            flarum_client_instance=flarum))
        chunk=ContextChunk('ops','D0','synthetic','main','0'*40,'update-workflow.md','Synthetic operations evidence')
        generated=ComprehensiveResponsesResult(report={'state':'ANSWERED',
            'summary':'현재 질문은 웹 트래픽 부하분산과 CubeOS의 승인된 업데이트 절차이며 이전 배포 장애와 다른 운영 주제입니다.',
            'recommendedActions':['Mold 네트워크 오퍼링의 LB 제공 여부와 별도 게스트 Nginx를 구분합니다.',
                                  'CubeOS의 ISO 기반 업데이트와 무인 정기 업데이트를 구분합니다.'],
            'unknowns':['설치 버전별 적용 범위는 기술지원센터 확인 대상입니다.']},citations_used=(),
            requested_model_id='mock',returned_model_id='mock',request_id='ops',response_id='ops')
        payload={'discussionId':'209','discussionUrl':'https://community.ablecloud.io/d/209',
            'authorId':'112','postAuthorId':'112','postId':'601','postNumber':11,
            'title':'CCVM 배포중 오류 문제','question':CURRENT}
        headers={'X-Correlation-Id':'operational-test','Idempotency-Key':'operational-test'}
        with patch.object(flarum,'post_is_visible',return_value=True), \
             patch.object(flarum,'visible_post_ids',return_value={'601','602'}), \
             patch.object(flarum,'publish_assistant_reply',return_value={'postId':'602','postUrl':'https://community.ablecloud.io/d/209/12'}) as publication, \
             patch('app.main.context_from_results',return_value=(chunk,)), \
             patch.object(adapter,'generate_comprehensive',return_value=generated) as provider, \
             patch('app.main.resolution_progress_result',side_effect=AssertionError('old solution acknowledgement')), \
             patch('app.main.reinstall_reset_result',side_effect=AssertionError('old topic shortcut')):
            response=client.post('/v1/community/cases',json=payload,headers=headers)
            self.assertEqual(201,response.status_code,response.text)
            answer=response.json()['data']['draftAnswer']
            self.assertIn('각 항목',answer)
            self.assertNotIn('먼저 다음 해결',answer)
            self.assertNotIn('해결되지 않으면',answer)
            again=client.post('/v1/community/cases',json=payload,headers=headers)
            self.assertEqual('602',again.json()['data']['publishedPostId'])
            publication.assert_called_once()
            provider.assert_called_once()

    def test_query_without_grounding_preserves_explanatory_referral_for_vulnerability(self):
        adapter=MockResponsesAdapter()
        client=TestClient(create_app(Settings(),MemoryStore(),responses_adapter=adapter))
        with patch('app.main.context_from_results',return_value=()),patch.object(adapter,'generate_comprehensive') as provider:
            response=client.post('/v1/assist/query',json={'queryId':str(uuid4()),'actorId':'operator',
                'question':'CVE-2026-123456 대상 Java 버전인지 확인 가능한가요?','productVersion':'diplo'},
                headers={'X-Correlation-Id':'vulnerability-referral'})
        self.assertEqual(200,response.status_code,response.text)
        data=response.json()['data']
        self.assertEqual('ABSTAINED',data['state'])
        self.assertEqual('EXPLANATION',data['answerIntent'])
        self.assertNotIn('문제가 발생한 시각',format_public_answer(data))
        provider.assert_not_called()

    def test_current_correction_outranks_quote_and_old_ccvm_title(self):
        wrapped='[Community 기술지원 제목]\nCCVM 배포중 오류\n\n[최초 질문]\nCommand execution test failed\n\n[참여자의 최신 추가 정보 또는 질문]\n'+CURRENT+'\n\n[직전 TechFlow 답변]\n콘솔 프록시'
        self.assertEqual(('WEB_TRAFFIC','CUBE_UPDATE'),operation_topics(wrapped))
        self.assertNotIn('command execution test failed',current_operation_text(wrapped))
        anchors=feature_source_terms(wrapped)
        for term in ('CreateLoadBalancerRuleCmd','ablestack_update.py','upstream'):
            self.assertIn(term,anchors)
        for term in ('insertScvmHost','create_ccvm_cloudinit.py','console proxy'):
            self.assertNotIn(term,anchors)

    def test_current_ops_select_all_reviewed_features_not_console_or_install_absence(self):
        refs=curated_platform_results(CURRENT)
        selected=select_context_results(CURRENT,{'CURATED_PLATFORM_REFERENCE':refs,'CLOUD_DIPLO':[
            {'path':'ConsoleAccessManagerImpl.java','content':'Mold console'},
            {'path':'LibvirtConsoleProxyLoadCommandWrapper.java','content':'load balancing'}]})
        paths='\n'.join(v['path'] for v in selected)
        for term in ('ablestack_update.py','network%26traffic','nginx.org'):
            self.assertIn(term,paths)
        self.assertNotIn('ConsoleProxy',paths)
        self.assertNotIn('ConsoleAccess',paths)

    def test_hci_shutdown_uses_full_restart_document(self):
        question='HCI를 퇴근할 때 종료하고 다시 기동하는 안전한 방법이 무엇인가요?'
        self.assertEqual(('HCI_POWER',),operation_topics(question))
        self.assertIn('system-restart-hci.md',feature_source_terms(question))
        refs=curated_platform_results(question)
        self.assertTrue(any('수동 사전 작업' in v['content'] for v in refs))
        self.assertTrue(any('시스템 VM' in v['content'] for v in refs))

    def test_actual_incident_and_kb_synthesis_are_not_reclassified(self):
        for question in ('nginx 웹 부하분산 설정 후 오류가 발생합니다.',
                         'HCI 전원 종료가 실패합니다.',
                         '[최종 Knowledge Base] HCI 전체 종료 절차가 해결되었습니다.'):
            self.assertFalse(nonincident_operation(question),question)
        self.assertFalse(nonincident_operation('CCVM command execution test failed'))
        self.assertIn('insertScvmHost',feature_source_terms('CCVM command execution test failed'))

    def test_vulnerability_applicability_has_no_incident_time_or_log_request(self):
        self.assertTrue(nonincident_operation('CVE-2026-123456 취약 대상 Java 버전인지 확인 가능한가요?'))
        self.assertTrue(nonincident_operation('CVE-2026-123456에 해당하는 취약 버전인가요?'))
        self.assertFalse(nonincident_operation('CVE-2026-123456 공격받아 오류가 발생했습니다.'))
        answer=format_public_answer({'state':'ABSTAINED','answerIntent':'EXPLANATION'})
        self.assertIn('기술지원센터',answer)
        for term in ('문제가 발생한 시각','로그','스크린샷'):
            self.assertNotIn(term,answer)

    def test_explanatory_answer_does_not_use_incident_template(self):
        answer=format_public_answer({'state':'ANSWERED','answerIntent':'EXPLANATION','report':{
            'summary':'Mold의 트래픽 부하분산과 게스트 Nginx 구성을 구분합니다.',
            'recommendedActions':['네트워크 오퍼링의 LB 제공 여부를 확인합니다.'],
            'unknowns':['설치 버전별 적용 범위는 기술지원센터에서 확인합니다.']}})
        self.assertNotIn('먼저 다음 해결',answer)
        self.assertNotIn('해결되지 않으면',answer)
        self.assertIn('각 항목',answer)

    def test_prohibited_command_remains_inline_not_copyable_executable_block(self):
        answer=format_public_answer({'state':'ANSWERED','report':{
            'summary':'관리 화면으로 처리합니다.',
            'recommendedActions':['직접 `virsh migrate`를 실행하지 마십시오. Mold에서 지원되는 기능을 사용합니다.'],
            'unknowns':[]}})
        self.assertIn('`virsh migrate`',answer)
        self.assertNotIn('```',answer)
