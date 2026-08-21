# Community 플랫폼 통합 E2E Runbook

## 목적

Community의 사용자 질문부터 AI 답변, 연속 대화, 해결 선택, Knowledge Base 전환까지를 운영 비밀정보나 고객 데이터를 저장소에 남기지 않고 반복 검증한다.

## 사전 조건

- Flarum, AI Gateway, Community Poller, Artifact Maintainer가 healthy 상태다.
- 인증정보는 런타임 Secret File 또는 운영자 입력으로만 사용한다.
- 합성 이미지와 합성 로그만 사용한다.
- GitHub→Chat 보호 서비스 Guard가 통과해야 한다.

## 절차

1. 인증된 시험 사용자로 제목에 `[TechFlow E2E]`를 포함한 토론을 만든다.
2. PNG 이미지 한 개와 로그 ZIP 한 개를 첨부한다.
3. Poller의 `delivered=1`과 Gateway의 `community_answer_auto_published`를 확인한다.
4. Flarum에서 AI 답변 Post가 공개됐는지 확인한다.
5. `community_chat_notification_sent`가 한 번 발생했는지 확인한다.
6. 같은 토론에 첫 답변을 참조하는 후속 질문을 등록한다.
7. 같은 Case ID와 증가한 `draftVersion`으로 후속 답변이 게시되는지 확인한다.
8. 사용자가 해결 답변을 선택한다.
9. `community_knowledge_base_published`와 `community_knowledge_base_solution_selected`를 확인한다.
10. Best Answer가 새 KB Post를 가리키는지 Flarum API와 브라우저에서 확인한다.
11. 보호 서비스 Guard와 컨테이너 ID·이미지·시작 시각을 다시 비교한다.

## 성공 기준

- 이미지와 로그 ZIP이 Artifact로 등록되고 경고 없는 분석이 수행된다.
- 첫 질문과 후속 질문이 같은 Case로 유지된다.
- 일반 답변은 친절한 엔지니어 문장으로 게시된다.
- 내부 Citation은 사용자 화면에 노출되지 않는다.
- KB는 `증상 / 원인 / 해결 방법 / 추가 고려사항 / 적용 버전` 구조다.
- KB Post가 최종 솔루션으로 자동 지정된다.
- 신규·후속·KB 완료 알림은 전송되고 정상 Heartbeat 알림은 전송되지 않는다.
- 보호 Webhook 서비스는 변경되지 않는다.

## 롤백과 정리

- 검증 실패 시 자동 게시·Poller만 중지하고 Flarum과 보호 Webhook은 유지한다.
- 실패한 시험 토론은 원인을 조사할 수 있도록 보존하되 실제 고객 데이터는 포함하지 않는다.
- 런타임 임시 스크립트와 평문 Secret은 즉시 제거한다.
- 저장소에는 ID, 상태, 시간, 비민감 로그 이벤트와 화면 증적만 남긴다.
