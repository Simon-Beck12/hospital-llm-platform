"""LLM으로 가는 텍스트에서 개인정보(PII)를 가린다.

규칙은 rrn → phone → mrn → email 순서로 적용한다.
숫자 경계는 \\b 대신 (?<!\\d), (?!\\d)를 쓴다. 파이썬 유니코드 정규식에서는 한글도 단어 문자라서
"010-1234-5678입니다"처럼 한글이 바로 붙으면 \\b가 맞지 않기 때문이다.
원본 값은 어디에도 남기지 않고 건수만 돌려준다.
"""

import copy
import re
from typing import Any

_RRN = re.compile(
    r"(?<!\d)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])-?[1-8]\d{6}(?!\d)"
)
_PHONE = re.compile(
    r"(?<!\d)(?:01[016789]|02|0[3-6][1-5])-?\d{3,4}-?\d{4}(?!\d)"
)
_MRN = re.compile(r"(환자번호|등록번호|[Mm][Rr][Nn])(\s*[:：]?\s*)\d{6,10}(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

PII_KINDS = ("rrn", "phone", "mrn", "email")


def _empty_counts() -> dict[str, int]:
    return dict.fromkeys(PII_KINDS, 0)


def mask_text(text: str) -> tuple[str, dict[str, int]]:
    """text의 PII를 자리표시자로 바꾸고 (가린 문자열, 종류별 건수)를 돌려준다."""
    counts = _empty_counts()
    text, counts["rrn"] = _RRN.subn("[주민번호]", text)
    text, counts["phone"] = _PHONE.subn("[전화번호]", text)
    text, counts["mrn"] = _MRN.subn(lambda m: f"{m.group(1)}{m.group(2)}[환자번호]", text)
    text, counts["email"] = _EMAIL.subn("[이메일]", text)
    return text, counts


def _add(total: dict[str, int], part: dict[str, int]) -> None:
    for kind, n in part.items():
        total[kind] = total.get(kind, 0) + n


def mask_messages(messages: list[Any]) -> tuple[list[Any], dict[str, int]]:
    """chat messages의 content를 가린 새 목록과 건수를 돌려준다. 원본은 바꾸지 않는다.

    content가 문자열이면 그대로 가리고, 리스트면 type이 "text"인 항목의 text만 가린다.
    """
    total = _empty_counts()
    new_messages = copy.deepcopy(messages)
    for message in new_messages:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            message["content"], counts = mask_text(content)
            _add(total, counts)
        elif isinstance(content, list):
            for part in content:
                if (
                    isinstance(part, dict)
                    and part.get("type") == "text"
                    and isinstance(part.get("text"), str)
                ):
                    part["text"], counts = mask_text(part["text"])
                    _add(total, counts)
    return new_messages, total
