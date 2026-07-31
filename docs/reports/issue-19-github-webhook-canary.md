# Issue #19 GitHub Webhook canary

이 파일은 TechFlow의 저장소 단위 GitHub Webhook 카나리 검증을 위해 생성했다.

- 대상 이벤트: `push`, `pull_request.closed` (`merged=true`)
- 전달 경로: GitHub → Event Gateway → Activepieces → Synology Chat Adapter
- 목적: 조직 Webhook 전환 전에 실제 GitHub 전달과 PR 병합 이벤트를 검증
- 비밀정보: 저장하지 않음

최종 실행 결과와 전달 ID는 Issue #19 검증 보고서에서 관리한다.

2차 카나리는 Push와 PR Merge가 연속 도착할 때 Chat 전송 간격이 0.5초 이상 유지되는지 검증한다.

최종 카나리는 전환된 조직 Webhook 하나만으로 Push와 PR Merge가 모두 성공하는지 검증한다.
