"""Bounded capability/change-impact reviews, separate from incident troubleshooting."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


MODE = 'CAPABILITY_REVIEW'
_SIGNAL = re.compile(r'지원|가능|상관없|영향|문제\s*없|해도|설정요청|적용하려', re.I)
_SECURITY = re.compile(r'계정|비밀번호|패스워드|암호|ssh|포트|보안|root|admin|권한', re.I)
_PLANNED_CHANGE = re.compile(r'변경|추가|생성|허용|사용|로그인|제한|차단|전환|만료|잠금|지원\s*여부', re.I)
_INCIDENT = re.compile(r'발생했|발생하였|실패했|접속이?\s*안\s*(?:됩|돼|되)|동작하지\s*않|오류가\s*발생해', re.I)
_HOWTO = re.compile(r'(?:명령어|설정\s*방법|변경\s*방법|절차).{0,12}(?:알려|안내|설명)', re.I)
_NUMBER = re.compile(r'^\s*(?:\d{1,2}[.)]\s*|[①②③④⑤⑥]\s*)')
_VERDICT = re.compile(r'^\s*\[(가능|불가|조건부 가능|확인 불가)\]\s*(.+)', re.S)
_INCIDENT_REQUEST = re.compile(r'(?:발생|장애|오류)\s*(?:시각|시간)|로그.{0,24}(?:보내|제공해|올려|알려)|(?:버전|구성).{0,16}알려\s*주', re.I|re.S)
_EXECUTION = re.compile(r'```|\b(?:sudo|systemctl|journalctl|virsh|usermod|useradd|passwd|firewall-cmd|semanage)\s', re.I)


@dataclass(frozen=True)
class CapabilitySpec:
    original: str
    items: tuple[str, ...]


def latest_question(value: str) -> str:
    text = value.strip()
    for marker in ('[현재 문의]\n', '[참여자의 최신 추가 정보 또는 질문]\n', '현재 질문:\n'):
        if marker in text:
            return text.split(marker, 1)[1].split('\n\n[', 1)[0].strip()
    return text


def capability_review_spec(value: str) -> CapabilitySpec | None:
    text = latest_question(str(value or ''))
    if not text or len(text.encode('utf-8')) > 2500 or not _SIGNAL.search(text):
        return None
    if _INCIDENT.search(text) or _HOWTO.search(text):
        return None
    normalized = re.sub(r'(?<=[?？])\s+(?=\d{1,2}[.)]\s)', '\n', text)
    items = []
    for line in normalized.splitlines():
        line = line.strip()
        numbered = bool(_NUMBER.match(line))
        clean = _NUMBER.sub('', line).strip()
        if clean and (clean.endswith(('?', '？')) or (numbered and _SIGNAL.search(clean))):
            items.append(clean)
    if not items and _SECURITY.search(text):
        items = [text]
    expected = re.search(r'(?:아래|다음)\s*(\d+)\s*(?:가지|개|항목)', text)
    if expected and int(expected[1]) != len(items):
        return None  # Never silently omit a question whose boundary was not preserved.
    if not 1 <= len(items) <= 6 or (len(items) == 1 and not (_SECURITY.search(text) and _PLANNED_CHANGE.search(text))):
        return None
    return CapabilitySpec(text, tuple(items))


def capability_question(spec: CapabilitySpec, *, limit: int = 4000) -> str:
    policy = (
        '\n\n[답변 형식]\n기능·지원·변경 가능 여부 문의이며 장애 진단이 아닙니다. '
        f'원문의 {len(spec.items)}개 질문을 같은 순서로 각각 답하십시오. '
        'recommendedActions에는 질문당 한 개의 완결된 답변만 넣고, 각 답변을 '
        '[가능], [불가], [조건부 가능], [확인 불가] 중 하나로 시작하십시오. '
        '각 항목의 결론·제품 소스 근거·적용 조건을 설명하십시오. 한 질문에 여러 제품이 있으면 모두 구분하십시오. '
        '기능 구현과 고객 설치 버전의 공식 지원 보증을 구분하고, 소스로 확인 불가한 범위는 '
        'ABLECLOUD 기술지원센터 문의로 안내하십시오. 모르는 항목을 가능하다고 만들지 마십시오. '
        '진단 로그·장애 시각·버전을 먼저 요구하거나 실행 명령/재시작 순서를 제시하지 마십시오. '
        'diagnoses는 비우고 unknowns에는 확인되지 않은 지원 범위만 적으십시오. '
        '관련 없는 기능·구현 클래스는 공개 답변에 나열하지 마십시오.'
    )
    text = '[기능·지원 검토]\n[현재 문의]\n' + spec.original + policy
    if len(text.encode('utf-8')) > limit:
        # Keep every question; trim neither item count nor item text.
        text = '[기능·지원 검토]\n[현재 문의]\n' + '\n'.join(spec.items) + policy
    if len(text.encode('utf-8')) > limit:
        compact = (f'\n\n[답변 형식]\n기능 지원 검토: {len(spec.items)}개 질문별 recommendedActions 한 개씩 같은 순서로 '
                   '[가능]/[불가]/[조건부 가능]/[확인 불가] 결론·근거·조건을 답하십시오. '
                   '소스 구현과 설치 버전 지원을 구분하며 미확인은 기술지원센터로 안내합니다. '
                   '로그·장애시각·버전 요청과 실행 명령은 금지합니다. diagnoses는 비웁니다.')
        text = '[기능·지원 검토]\n[현재 문의]\n' + '\n'.join(spec.items) + compact
    if len(text.encode('utf-8')) > limit:
        raise ValueError('capability questions exceed the requested prompt budget')
    return text


def _products(text: str) -> set[str]:
    return {name for name, pattern in (('CubeOS', r'cube\s*os'), ('Mold', r'\bmold\b'), ('Wall', r'\bwall\b'))
            if re.search(pattern, text, re.I)}


def prepare_capability_result(result: dict[str, Any], spec: CapabilitySpec | None) -> dict[str, Any]:
    """Keep provider failures, and safely refer unclear coverage without inventing a verdict."""
    if spec is None or result.get('state') == 'FAILED':
        return result
    value = dict(result)
    report = dict(result.get('report') or {})
    actions = list(report.get('recommendedActions') or [])
    unknowns = list(report.get('unknowns') or [])
    answers = []
    valid = value.get('state') == 'ANSWERED' and len(actions) == len(spec.items)
    for question, action in zip(spec.items, actions):
        if not isinstance(action, str):
            valid = False
            break
        match = _VERDICT.match(action)
        if not match or _EXECUTION.search(action) or _INCIDENT_REQUEST.search(action):
            valid = False
            break
        verdict, body = match.groups()
        required = _products(question)
        if len(required) > 1 and not required <= _products(body):
            valid = False
            break
        if verdict == '확인 불가' and '기술지원센터' not in body:
            body += ' 공식 지원 여부는 ABLECLOUD 기술지원센터에 문의해 주세요.'
        answers.append({'question': question, 'verdict': verdict, 'answer': body.strip()})
    if any(not isinstance(note, str) or _INCIDENT_REQUEST.search(note) or _EXECUTION.search(note) for note in unknowns):
        valid = False
    if not valid:
        # Ambiguous position/count is not grounds for mapping a partial answer to a different question.
        answers = [{'question': item, 'verdict': '확인 불가',
                    'answer': '현재 근거로 이 항목의 지원 여부와 적용 조건을 확정할 수 없습니다. '
                              'ABLECLOUD 기술지원센터에 공식 지원 범위를 문의해 주세요.'} for item in spec.items]
        value['state'] = 'ABSTAINED'
        report.update(state='ABSTAINED', currentAssessment='INSUFFICIENT_EVIDENCE', diagnoses=[],
                      summary='질문별 지원 여부와 적용 조건을 명확히 확인하지 못했습니다.',
                      recommendedActions=['[확인 불가] '+row['answer'] for row in answers], unknowns=[],
                      confidence='LOW', abstainReason='capability-coverage-incomplete',
                      previewAssessment='NOT_APPLICABLE', previewGuidance=None)
        value['capabilityReferralFallback'] = True
        unknowns = []
    else:
        report.update(diagnoses=[], recommendedActions=[f'[{row["verdict"]}] {row["answer"]}' for row in answers])
    value.update(answerIntent='EXPLANATION', answerMode=MODE, capabilityAnswers=answers,
                 capabilityQuestionCount=len(spec.items), capabilityUnknowns=unknowns, report=report)
    return value


def capability_result_complete(result: dict[str, Any]) -> bool:
    if result.get('answerMode') != MODE or result.get('state') not in {'ANSWERED', 'ABSTAINED'}:
        return False
    rows = result.get('capabilityAnswers') or []
    return 1 <= len(rows) <= 6 and len(rows) == result.get('capabilityQuestionCount') and all(isinstance(row, dict) and row.get('question') and row.get('answer')
        and row.get('verdict') in {'가능','불가','조건부 가능','확인 불가'}
        and not _EXECUTION.search(row['answer']) and not _INCIDENT_REQUEST.search(row['answer'])
        and (result.get('state') != 'ABSTAINED' or (row['verdict'] == '확인 불가' and '기술지원센터' in row['answer'])) for row in rows)
