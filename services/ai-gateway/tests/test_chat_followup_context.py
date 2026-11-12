import unittest

from app.conversation import build_chat_question
from app.official_web import guest_os_context_label, guest_os_family, support_family, support_topic, allowed_domains_for_question


class ChatFollowupContextTests(unittest.TestCase):
    def history(self, os='Ubuntu 22.04'):
        return [{'role':'USER','content':f'{os} 가상머신에서 시간 동기화 상태 확인 방법을 알려주세요.'},
                {'role':'ASSISTANT','content':'Mold API가 아니라 VM 안에서 timedatectl 상태를 확인합니다.'}]

    def test_actual_issue150_followup_keeps_user_os_not_assistant_product_name(self):
        question = '앞서 말한 그 가상머신에서 동기화 여부를 어떤 출력값으로 판단하면 될까요?'
        prompt = build_chat_question(self.history(), question)
        self.assertEqual('UBUNTU', guest_os_family(prompt))
        self.assertEqual('UBUNTU', support_family(prompt))
        self.assertEqual('TIME_SYNC', support_topic(prompt))
        self.assertEqual(('documentation.ubuntu.com','packages.ubuntu.com'), allowed_domains_for_question(prompt))
        self.assertIn('Ubuntu 22.04', prompt.split('현재 질문:\n')[-1])
        self.assertTrue(prompt.endswith(question))

    def test_os_families_and_versions_remain_available_in_ellipsis_followups(self):
        for os,family in (('Debian 12','DEBIAN'),('Rocky Linux 9.6','RHEL_FAMILY'),
                          ('Windows Server 2022','WINDOWS'),('윈도우즈 서버2022','WINDOWS'),('FreeBSD 14.2','FREEBSD'),
                          ('macOS 14','MACOS'),('Oracle Linux 9','ORACLE_LINUX')):
            with self.subTest(os=os):
                prompt=build_chat_question(self.history(os),'그 VM에서 그 출력값은 어떤 의미인가요?')
                self.assertEqual(family,guest_os_family(prompt))
                self.assertEqual('TIME_SYNC',support_topic(prompt))
                self.assertIn(os,prompt.split('현재 질문:\n')[-1])

    def test_explicit_os_change_wins_without_prior_environment_hint(self):
        prompt=build_chat_question(self.history(),'그 VM 대신 Debian 12에서 시간 동기화 확인 방법은요?')
        self.assertEqual('DEBIAN',guest_os_family(prompt))
        self.assertNotIn('이전 사용자 질문에 명시된 환경',prompt)

    def test_same_specific_topic_is_continuous_without_repeating_a_pronoun(self):
        prompt=build_chat_question(self.history(),'동기화가 정상인지 출력에서 확인하는 기준은요?')
        self.assertEqual('UBUNTU',guest_os_family(prompt))
        self.assertEqual('TIME_SYNC',support_topic(prompt))

    def test_unrelated_specific_topic_without_a_reference_does_not_guess_the_vm(self):
        prompt=build_chat_question(self.history(),'SMB 공유 폴더 마운트 방법을 알려주세요.')
        self.assertIsNone(guest_os_family(prompt))

    def test_a_different_vm_is_not_assumed_to_have_the_previous_os(self):
        for question in ('다른 VM에서 시간 동기화 상태를 확인하려면요?',
                         '다른 서버에서 시간 동기화 상태를 확인하려면요?',
                         'different VM에서 시간 동기화 상태를 확인하려면요?',
                         '그 VM의 운영체제를 변경했습니다. 시간 동기화 상태를 확인하려면요?'):
            prompt=build_chat_question(self.history(),question)
            self.assertIsNone(guest_os_family(prompt))

    def test_new_topic_on_same_os_does_not_inherit_old_time_topic(self):
        prompt=build_chat_question(self.history(),'그 VM에서 SMB 공유 폴더를 마운트하는 방법은요?')
        self.assertEqual('UBUNTU',guest_os_family(prompt))
        self.assertEqual('SMB_MOUNT',support_topic(prompt))
        self.assertNotIn('이전 사용자 질문 주제: 시간 동기화',prompt)

    def test_product_question_and_explicit_reset_do_not_force_guest_os(self):
        for question in ('그 VM을 Mold에서 스냅샷 생성할 때 실패합니다.',
                         '다른 질문입니다. 그 VM의 설정을 확인하려면요?'):
            with self.subTest(question=question):
                prompt=build_chat_question(self.history(),question)
                self.assertNotIn('이전 사용자 질문에 명시된 환경',prompt)
                self.assertIsNone(guest_os_family(prompt))

    def test_new_conversation_and_assistant_only_history_cannot_supply_os(self):
        for history in ([],[{'role':'ASSISTANT','content':'Ubuntu 22.04라고 가정하겠습니다.'}]):
            prompt=build_chat_question(history,'그 VM에서 그 출력값은 어떤 의미인가요?')
            self.assertIsNone(guest_os_family(prompt))

    def test_recent_product_or_ambiguous_user_turn_is_a_context_boundary(self):
        for newer in ('Mold에서 VM 스냅샷이 실패합니다.',
                      '다른 질문으로 바꾸겠습니다.',
                      'Ubuntu와 Windows를 비교하고 있습니다.'):
            history=[*self.history(),{'role':'USER','content':newer}]
            prompt=build_chat_question(history,'그 VM에서 그 출력값은 어떤 의미인가요?')
            self.assertIsNone(guest_os_family(prompt))

    def test_same_os_new_unmapped_subject_does_not_revive_older_time_topic(self):
        history=[*self.history(),{'role':'USER','content':'그 VM에서 SSH 접속 설정 방법을 알려주세요.'}]
        prompt=build_chat_question(history,'앞서 말한 그 VM의 출력 결과를 해석하는 방법은요?')
        self.assertEqual('UBUNTU',guest_os_family(prompt))
        self.assertNotIn('이전 사용자 질문 주제: 시간 동기화',prompt)

    def test_safe_label_never_copies_addresses_credentials_or_ambiguous_comparisons(self):
        self.assertEqual('Ubuntu 22.04',guest_os_context_label('Ubuntu 22.04 VM입니다. token=private host=10.0.0.8'))
        self.assertEqual('Ubuntu',guest_os_context_label('Ubuntu 10.0.0.8'))
        self.assertIsNone(guest_os_context_label('Ubuntu와 Windows 비교'))
        self.assertIsNone(guest_os_context_label('token=Ubuntu22.04'))
        for text in ('ssh ubuntu@server', '/home/ubuntu/log.txt', 'https://ubuntu.example.com/path'):
            self.assertIsNone(guest_os_context_label(text))

    def test_hypervisor_environment_is_not_silently_reused_as_guest_environment(self):
        history=[{'role':'USER','content':'Ubuntu 22.04 KVM 호스트입니다.'}]
        self.assertIsNone(guest_os_family(build_chat_question(history,'그 VM에서 그 값은 어떤 뜻인가요?')))

    def test_explicit_new_environment_after_topic_reset_is_available_to_its_own_followup(self):
        history=[*self.history(),{'role':'USER','content':'다른 질문입니다. Debian 12 VM의 시간 동기화 확인 방법은요?'}]
        prompt=build_chat_question(history,'그 VM에서 출력값을 어떻게 해석하나요?')
        self.assertEqual('DEBIAN',guest_os_family(prompt))
        self.assertIn('Debian 12',prompt.split('현재 질문:\n')[-1])

    def test_linux_reference_does_not_inherit_a_prior_windows_environment(self):
        prompt=build_chat_question(self.history('Windows Server 2022'),'그 Linux VM에서 출력값을 어떻게 해석하나요?')
        self.assertEqual('GENERIC_LINUX',guest_os_family(prompt))
        self.assertNotIn('이전 사용자 질문에 명시된 환경',prompt)

    def test_hint_survives_history_compaction_and_preserves_utf8_boundary(self):
        history=[self.history()[0],*[{'role':'ASSISTANT','content':'긴 이전 설명입니다. '*500} for _ in range(20)]]
        question='그 VM에서 출력값은 어떻게 해석하나요?'
        prompt=build_chat_question(history,question,limit=1800)
        self.assertLessEqual(len(prompt.encode('utf-8')),1800)
        self.assertEqual('UBUNTU',guest_os_family(prompt))
        self.assertTrue(prompt.endswith(question))


if __name__=='__main__':
    unittest.main()
