# Chat 후속 질문의 게스트 OS 맥락 보완

관련 Issue: #150. 변경 버전: 0.16.30.

## 원인과 보완

실제 배포 검증에서 첫 Ubuntu22.04 시간 동기화 질문은 정상 응답했으나, 같은 대화의 "앞서 말한 그 가상머신" 후속 질문은 불필요한 Diplo 버전·장애 로그 요청으로 바뀌었다. 저장된 대화와 종합 질문에는 Ubuntu가 있었지만 공식 자료 분류가 최신 문장만 확인해 OS family가None이었다. 첫 AI 답변에 있던 부정 설명인 "Mold API가 아닌 OS 조회"의 제품명도 후속 분류에 혼선을 줄 수 있었다.

대화를 무조건 과거 OS로 분류하는 대신, 같은 활성 대화에서 사용자가 직접 제공한 환경을 제한적으로 참고한다.

- 명확한 지시어·연속 질문 또는 동일한 구체 주제가 있을 때만 이전 `USER` 발언을 역순으로 확인한다. AI 답변만으로 OS를 추정하지 않는다.
- OS 이름·인접 버전과 제한된 주제만 최신 질문 앞의 참고 정보로 보존한다. 사용자 현재 원문은 유지하며 전체 UTF-8 예산도 유지한다.
- 최신 질문에 명시된 OS·버전이 최우선이다. 다른 VM·새 주제·제품/호스트 질문이나 여러 OS 비교는 오래된 환경을 강제 상속하지 않는다.
- 같은 OS에서 SMB 등 다른 주제로 바뀌면 이전 시간 동기화 주제를 붙이지 않는다.
- 토큰/암호 형태, URL·경로·SSH 사용자명에서 OS 이름을 뽑아 환경으로 오인하지 않도록 제한한다. 기존 외부 검색 도메인 allowlist와 비밀정보 처리 정책은 변경하지 않는다.
- 긴 이력이 잘려도 현재 질문의 작은 환경 참고는 보존된다. 해결 후 새 대화는 이전 Turn을 전달받지 않으므로 OS를 상속하지 않는다.

## 시험

재현 사례와 Ubuntu·Debian·Rocky Linux·Windows Server·FreeBSD·macOS·Oracle Linux의 연속 질문, OS 변경, 주제 변경, 새 대화, AI-only 이력, 호스트/게스트 분리, 민감정보·경로 오인 방지와 UTF-8 상한을 자동 시험한다.

관련13개 모듈의 **340개 회귀시험**을 실행한다. 배포 이미지에서는 Linux 전체 시험을 별도로 실행한 뒤 운영에 반영한다. 단위 시험의 여러 OS 분류 통과를 모든 OS의 실사용 E2E로 과장하지 않는다.

```text
python -m unittest tests.test_chat_followup_context tests.test_official_web tests.test_conversation tests.test_community tests.test_community_poller tests.test_store tests.test_postgres_store tests.test_versioned_assist tests.test_chat_assist tests.test_epic4_operations tests.test_responses tests.test_community_kb_refresh tests.test_community_review_candidates
```

## 운영 검증과 경계

사용자가 새 PR의 병합·제한 배포를 승인했다. Gateway/Poller만 같은 이미지로 교체하고, 진행 중 Job과 Community 대기를 확인한 뒤 전환한다. DB·Poller 상태·기존 코드/Compose와 롤백 이미지를 보존한다. DB 스키마 변경은 없다. GitHub→Chat 및 다른 서비스는 변경하지 않는다.

등록된 운영자 계정의 종료된 대화에서 텍스트 전용 합성 질문2건으로 실제 접수·AI 분석·Bot 전송과 후속 답변 내용을 다시 확인한다. 첨부·네이티브 Chat UI 입력까지 시험했다고 주장하지 않는다. 실제 고객 대화에 새 Turn이 들어오면 테스트 종료 처리를 하지 않는다. Community도 검증용 토론의 자동 게시·재전달 중복 방지를 확인하고 해당 토론만 숨김 정리한다.

최종 병합 커밋·이미지·시험 건수·실제 E2E 결과는 연결 PR의 운영 반영 댓글에 남긴다. 결과가 불충분하면 정상 완료로 처리하지 않는다.
