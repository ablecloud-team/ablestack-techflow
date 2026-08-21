# Epic #4 사내 Assist 실증 완료 보고서

## 1. 결론

TechFlow AI Gateway 0.15.0은 GitHub→Chat Webhook, Community AI 자동 답변·연속 대화·KB 생성, 사내 Chat 직접 기술지원의 세 시나리오를 하나의 운영 기준으로 제공한다. Chat과 Community는 독립 채널이지만 DOC·Diplo·관련 코드·Europa Preview 검토, 공개 답변 안전화, Artifact 처리, 실패 복구와 KPI 정책을 공유한다.

## 2. 구현 범위

- Chat 사용자별 Conversation·Turn·Context Version과 `해결` 종료
- Community 성공 후 체크포인트, 실패 Event 재처리와 답변 멱등성
- 지수 백오프·Dead Letter·수동 재처리
- 같은 장애의 최초 알림과 실제 복구 알림만 전송
- Community·Chat·Source Coverage·Artifact·장애 비식별 KPI
- LF 강제 배포 패키지와 Windows CRLF 계약 테스트
- 보호된 GitHub→Chat 서비스 무변경 검증

## 3. 검증 결과

| 검증 | 기준 | 결과 |
|---|---|---|
| 단위·계약 테스트 | 전 항목 통과 | 271건 통과 |
| 셸 스크립트 | 배포 Archive CRLF 0건 | 통과 |
| Chat 연속 대화 | 후속 질문 맥락 유지, 해결 후 새 Context | 통과 |
| Chat 근거 노출 | 일반 답변 0건, 명시 명령만 허용 | 통과 |
| 실패 알림 | 동일 장애 최초 1회 | 통과 |
| 복구 알림 | 실제 복구 최초 1회 | 통과 |
| 정상 주기 알림 | 0회 | 통과 |
| Dead Letter | 3회 실패 후 전환 | 통과 |
| 수동 재처리 | RETRYING 전환 | 통과 |
| KPI | 원문·Source 상세 미포함 | 통과 |
| 운영 배포 | Gateway 0.15.0 Healthy, Poller Running | 통과 |
| 공개 서비스 | Community·Chat·Activepieces HTTP 200 | 통과 |
| 보호 서비스 | Container·Image·StartedAt 변경 0건 | 통과 |

운영 배포와 실제 Chat·Community E2E 값은 [`production-e2e.json`](../evidence/epic-4/production-e2e.json)을 최종 권위 증적으로 사용한다.

### 3.1 실제 Chat E2E

- 첫 질문 답변 1,484자, 후속 질문 답변 1,428자
- 같은 사용자 Conversation에 User·Assistant 4 Turn 기록
- 후속 질문에서 앞 질문의 맥락 유지
- `해결` 입력 후 `RESOLVED`, Context Version 1 종료
- 통제된 장애와 복구에서 장애 알림 1회·복구 알림 1회·알림 전송 실패 0회

### 3.2 실제 Community E2E

- 운영 검증 Discussion #175를 Poller가 감지
- Case `a506515a-3be5-4d4c-887f-720b7e60fa29` 생성
- AI 답변 Post #411 자동 게시, 본문 4,328자
- 사용자 답변의 내부 Citation·Source 식별정보 노출 0건
- 시험 Discussion은 검증 직후 삭제하여 운영 목록 오염 방지

### 3.3 기동 중 연속성 관찰

Gateway와 Poller 동시 교체 직후 Poller가 Gateway보다 먼저 기동해 연결 실패 1회를 기록했다. 실패 Post는 체크포인트되지 않았고 같은 상태 파일로 자동 재시도되어 이후 67회 연속 정상 폴링했다. 이는 일시 장애 뒤 작업 유실 없이 복구되는 연속성 정책을 실제 운영 경로에서 확인한 결과다.

## 4. 서비스 연속성

Community Poller는 실패한 Post를 완료 목록에 기록하지 않는다. 따라서 일시적 Flarum·Artifact·Gateway·OpenAI 오류가 사라지면 같은 Event를 다시 처리한다. Gateway는 Discussion/Post 단위 멱등 키로 재전송을 하나의 Turn과 답변으로 수렴시킨다. Chat은 사용자별 최근 대화 맥락을 유지하며 해결 전까지 추가 자료 요청과 후속 답변을 반복한다. 운영 Poller는 Flarum 내부 주소를 처리 경로로 사용하고, 사용자 링크에는 공개 HTTPS 주소를 사용한다.

## 5. 보안과 데이터

비밀번호·토큰·API 키는 Runtime Secret으로만 사용한다. 장애 큐와 KPI에는 질문·답변·로그 원문을 저장하지 않는다. 사용자 답변은 Repository·Branch·Commit·Path·Line·Evidence ID를 제거한다. 내부 근거는 권한 있는 담당자가 `근거 <Case>`를 명시한 경우에만 제공한다.

## 6. Epic #5 이관

다음 단계는 [Epic #5 ABLESTACK Assist MVP 제품화 계획](../plans/epic5-assist-mvp-plan.md)이다. Tenant·RBAC·제품 UI·Release별 지식 수명주기·SLO를 추가하여 사내 실증을 제한 고객 Pilot으로 확장한다. 실제 자원 변경은 여전히 별도 Ops 승인 경계에 둔다.
