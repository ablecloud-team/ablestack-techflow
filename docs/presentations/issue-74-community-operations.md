# Issue #74 발표자료 구성

## 대상과 목적

- 대상: TechFlow 제품 책임자와 Community 운영 담당자
- 목적: 백업·복원·관측·보안 운영 기준과 운영 적용 결과 승인
- 핵심 결론: 운영 자동화와 WSL 전체 복원 실증을 완료해 Community 운영 판정은 GO

## 슬라이드

1. Community 운영 복구 기반을 실제 서버에 적용
2. 수동 백업 중심 기준선에서 자동·검증·경보 체계로 전환
3. DB·App·업로드를 한 시점으로 묶고 공개키로 암호화
4. 운영 서버에는 공개키만, WSL에는 복구 개인키만 보관
5. 운영 Snapshot을 9초에 복원하고 핵심 데이터 차이 0건 확인
6. 5분마다 서비스·HTTP·용량·백업·AI·Mail Driver를 확인
7. Chat은 상태 전이만 보내고 같은 장애는 1시간 억제
8. 5개 보안 Header·TLS·Rate Limit·권한·로그 정책 통과
9. Symfony Mailer 잔여 위험은 smtp 강제와 호환 업그레이드로 관리
10. 운영 GO, 승인된 Community Theme 활성화, 다음은 외부 Backup Vault와 분기 복원 훈련
