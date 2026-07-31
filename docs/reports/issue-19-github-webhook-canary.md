# Issue #19 GitHub Webhook canary

이 파일은 TechFlow의 저장소 단위 GitHub Webhook 카나리 검증을 위해 생성했다.

- 대상 이벤트: `push`, `pull_request.closed` (`merged=true`)
- 전달 경로: GitHub → Event Gateway → Activepieces → Synology Chat Adapter
- 목적: 조직 Webhook 전환 전에 실제 GitHub 전달과 PR 병합 이벤트를 검증
- 비밀정보: 저장하지 않음

최종 실행 결과와 전달 ID는 Issue #19 검증 보고서에서 관리한다.
