# Issue #115 Community 해결 상태 진행 확인 복구 보고서

## 1. 결론

Discussion #181의 Knowledge Base 누락은 해결 답변 Post #456이 일반 지원 사용자의 글이어서 발생한 것이 아니다. 질문자는 Post #456을 정상적으로 해결 답변으로 선택했지만, Community Poller가 최초 질문 Post #451의 Gateway 확인을 270회 반복하면서 해결 이벤트 단계로 진행하지 못했다.

AI Gateway 0.16.10에서 같은 Discussion의 Gateway Case가 더 뒤의 Post까지 처리했다면 앞선 Pending Post도 완료로 인정하고, Poller 실행 중 발견한 해결 토론은 이전 Snapshot이 없어도 해결 이벤트를 생성하도록 수정했다. 운영 Gateway·Poller에 제한 배포한 뒤 Discussion #181의 KB Post #465를 자동 게시·선택했고, 같은 Post를 정확한 도메인·계정 제한 안내로 보완했다.

## 2. 확인된 원인

| 구분 | 확인 결과 |
|---|---|
| 최초 질문 | Post #451 |
| AI 답변 | Post #452, Post #455 |
| 선택된 해결 답변 | 지원 사용자 Post #456 |
| 해결 선택 사용자 | 질문자 User #46 |
| Gateway 진행 위치 | `lastSeenPostId=456` |
| 남은 Poller 작업 | Post #451, 270회 재시도 |
| 토론 Snapshot | 없음 |
| 직접 원인 | Pending Post ID와 `lastSeenPostId`의 정확 일치만 완료로 인정 |
| 2차 원인 | Snapshot이 없는 신규 해결 토론은 해결 변경으로 판단하지 않음 |

Gateway가 같은 토론의 Post #456까지 기록했다면 Post #451도 이미 처리된 상태다. 그러나 정확 일치 조건 때문에 Post #451이 영구 대기했고, 토론 Snapshot과 해결 이벤트가 모두 생성되지 않았다.

## 3. 구현

- 같은 Discussion에서 숫자형 `lastSeenPostId`가 Pending Post ID보다 크면 이전 Post 처리 완료로 인정
- 숫자가 아닌 Post ID는 기존 정확 일치 판정 유지
- Poller 실행 중 새로 발견한 해결 토론은 Snapshot이 없어도 해결 이벤트 제출
- 최초 Bootstrap에서는 과거 해결 토론을 일괄 변환하지 않는 기존 안전장치 유지
- Discussion #181과 동일한 Post #451 → #456 진행·해결 회귀시험 추가
- AI Gateway 버전 0.16.10과 OpenAPI 39개 Operation 재생성

## 4. Discussion #181 복구

배포 후 첫 Poll에서 Post #451의 Pending 작업이 제거되고 Post #456 해결 이벤트가 제출됐다. Gateway는 `RESOLVED_BY_REQUESTER`를 기록한 뒤 KB Post #465를 게시하고 같은 Post를 최종 해결 답변으로 선택했다.

자동 초안의 `확인된 증상 정보가 없습니다` 문장은 실제 질문과 맞지 않아 같은 Post #465에서 다음 내용으로 보완했다.

- 도메인 제한은 하위 계정 전체의 합산 사용량을 제한
- 사용자는 계정에 소속되며 제한은 사용자 개인이 아닌 계정 기준으로 관리
- 새 계정의 기본 제한은 글로벌 설정의 `max.account.*`에서 결정
- 도메인 총한도, 새 계정 기본값, 기존 계정의 별도 제한을 구분해 설정
- 주요 `max.account.*` 항목과 `-1`의 의미
- 도메인 제한과 계정 제한이 동시에 적용되는 점
- 적용 버전 `ABLESTACK Diplo v4.6.1`

최종 Case는 원본 해결 Post #456, KB Post #465, KB 버전 2, 최종 솔루션 선택 완료 상태다. Poller의 전체 `pendingPosts`와 `pendingResolutions`는 모두 0건이다.

## 5. 검증 결과

| 항목 | 결과 |
|---|---|
| Community Poller 집중 시험 | 38건 통과 |
| WSL ext4 전체 시험 | 348건 통과 |
| 변경 파일 Ruff | 통과 |
| OpenAPI | 39개 Operation |
| Gateway | 0.16.10, Healthy, Restart 0 |
| Community Poller | 0.16.10, Healthy, Restart 0 |
| Discussion #181 KB Post | #465 |
| KB 원본 해결 Post | #456 |
| KB 버전 | 2 |
| 최종 솔루션 | Post #465 선택 완료 |
| Pending Post / Resolution | 0 / 0 |
| Community·Chat | HTTP 200 / 200 |
| 보호 서비스 변경 | 0건 |

브라우저에서 Discussion #181을 직접 열어 `해결됨`, `최종 해결 가이드`, `해결된 답변` 표시와 증상·원인·해결 방법·추가 고려사항·적용 버전 전체 내용을 확인했다.

## 6. 배포 안전성과 복구

최초 Windows 배포 압축본은 전역 `core.autocrlf=true`의 영향을 받아 셸 진입점이 CRLF로 변환됐다. Gateway 시작 검증에서 `/usr/bin/env: sh\r` 오류를 즉시 발견했고, 사전 백업의 0.16.9 소스·설정으로 Gateway·Poller만 복구했다. DB나 Community 게시물 변경 전이었으며 복구 후 두 서비스가 Healthy인 것을 확인했다.

재배포 패키지는 저장소의 `tools/package_ai_gateway.py`를 WSL에서 사용해 생성했고, 압축본과 컨테이너 이미지의 셸 진입점이 LF임을 바이트 단위로 확인한 뒤 적용했다.

- 배포 Commit: `bd44f72`
- 최종 이미지: `techflow/ai-gateway:issue115-0.16.10-bd44f72`
- 이미지 ID: `sha256:4231112f37b229d209edd9242e40fb95e5d2ad235fcf6fab38f6ca6db3be0827`
- 배포 패키지 SHA-256: `BF4645E140C5844EC110BFB443D57C131701ACAE6111B34C1F998B12E6CBED8D`
- 운영 백업: `/home/ablecloud/techflow-ai-gateway-backups/issue115-resolution-progress-20260910T014611Z`
- DB Schema 변경: 없음

## 7. 관련 자산

- Issue #115
- PR #110
- `docs/evidence/issue-115/discussion-181-kb-recovery.json`
