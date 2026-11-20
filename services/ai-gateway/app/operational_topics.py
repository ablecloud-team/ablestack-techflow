"""Current non-incident operations: source selection, not a support verdict."""
from __future__ import annotations

import re
from .support_intent import latest_question

ANCHORS = {
    'WEB_TRAFFIC': ('network&traffic-mngt-guide.md', 'windows-guide-web.md',
                    'CreateLoadBalancerRuleCmd', 'LoadBalancingRules', 'LoadBalancer',
                    'nginx', 'upstream', 'proxy_pass'),
    'CUBE_UPDATE': ('ablestack_update.py', 'update-workflow.md', 'update-all.sh',
                    'update-qemu-exec-tools.sh', 'UPDATE_SCRIPT_MAP'),
    'HCI_POWER': ('system-restart-hci.md', 'cube-admin-guide-ablestack-hci.md',
                  '전체 시스템 자동 종료', 'HEALTH_OK'),
    'SECURITY_APPLICABILITY': ('java', 'pom.xml', 'java.version', 'CVE'),
}
_WEB = re.compile(r'nginx|http|웹|트래픽', re.I)
_LB = re.compile(r'부하\s*분산|로드\s*밸런|load.?balanc', re.I)
_INCIDENT = re.compile(r'오류가?\s*발생|실패(?:했|합|해|하였)|접속이?\s*안|동작하지\s*않|침해|공격받', re.I)


def current_operation_text(value: str) -> str:
    text = latest_question(value)
    correction = re.search(r'위와\s*같은\s*의미가\s*아니라|그\s*뜻이\s*아니라', text)
    if correction:
        tail = text[correction.end():]
        if _WEB.search(tail) and _LB.search(tail):
            return tail.strip()  # Prior quoted migration advice is not the new request.
    return text


def operation_topics(value: str) -> tuple[str, ...]:
    if any(marker in value for marker in ('[최종 Knowledge Base]', '[Community 해결 답변 선택')):
        return ()
    text = current_operation_text(value)
    topics = []
    if _WEB.search(text) and _LB.search(text):
        topics.append('WEB_TRAFFIC')
    if re.search(r'cube|큐브|호스트.{0,8}(?:os|운영체제)', text, re.I) and re.search(r'업데이트|업그레이드|update|upgrade', text, re.I):
        topics.append('CUBE_UPDATE')
    if re.search(r'(?<![a-z0-9_])hci(?![a-z0-9_])|하이퍼컨버지드', text, re.I) and re.search(r'종료|퇴근|내렸다|재기동|전원|shutdown', text, re.I):
        topics.append('HCI_POWER')
    if re.search(r'(?<![a-z0-9_])CVE-\d{4}-\d{4,}(?![a-z0-9_])', text, re.I) and re.search(r'버전|취약|대상|영향|업데이트', text):
        topics.append('SECURITY_APPLICABILITY')
    return tuple(topics)


def nonincident_operation(value: str) -> bool:
    return bool(operation_topics(value)) and not _INCIDENT.search(current_operation_text(value))


def operational_source_terms(value: str) -> tuple[str, ...]:
    if not nonincident_operation(value):
        return ()
    return tuple(dict.fromkeys(term for topic in operation_topics(value) for term in ANCHORS[topic]))
