"""PII 마스킹 규칙 테스트. 모든 번호는 가짜다."""

import pytest

from app.masking import mask_messages, mask_text

SHOULD_MASK = [
    ("900101-1234567", "rrn", "[주민번호]"),
    ("9001011234567", "rrn", "[주민번호]"),
    ("외국인 900101-5234567", "rrn", "외국인 [주민번호]"),
    ("010-1234-5678", "phone", "[전화번호]"),
    ("01012345678", "phone", "[전화번호]"),
    ("02-123-4567", "phone", "[전화번호]"),
    ("031-1234-5678", "phone", "[전화번호]"),
    ("연락처는 010-1234-5678입니다", "phone", "연락처는 [전화번호]입니다"),
    ("환자번호: 12345678", "mrn", "환자번호: [환자번호]"),
    ("등록번호 1234567", "mrn", "등록번호 [환자번호]"),
    ("MRN：123456", "mrn", "MRN：[환자번호]"),
    ("test.user@example.com", "email", "[이메일]"),
]

SHOULD_NOT_MASK = [
    "901301-1234567",  # 13월
    "20261124",  # 날짜
    "수량 12345678개",  # 키워드 없는 숫자
    "버전 1.2.3",
    "010-12",  # 짧음
]


@pytest.mark.parametrize(("text", "kind", "expected"), SHOULD_MASK)
def test_should_mask(text: str, kind: str, expected: str) -> None:
    masked, counts = mask_text(text)
    assert masked == expected
    assert counts[kind] == 1
    assert sum(counts.values()) == 1


@pytest.mark.parametrize("text", SHOULD_NOT_MASK)
def test_should_not_mask(text: str) -> None:
    masked, counts = mask_text(text)
    assert masked == text
    assert sum(counts.values()) == 0


def test_counts_by_kind() -> None:
    masked, counts = mask_text("900101-1234567, 010-1234-5678, 환자번호: 12345678")
    assert counts == {"rrn": 1, "phone": 1, "mrn": 1, "email": 0}
    assert sum(counts.values()) == 3
    assert masked == "[주민번호], [전화번호], 환자번호: [환자번호]"


def test_mask_messages_does_not_change_original() -> None:
    original = [
        {"role": "user", "content": "전화 010-1234-5678"},
        {"role": "user", "content": [{"type": "text", "text": "test.user@example.com"}]},
    ]
    masked, counts = mask_messages(original)
    assert masked[0]["content"] == "전화 [전화번호]"
    assert masked[1]["content"][0]["text"] == "[이메일]"
    assert counts == {"rrn": 0, "phone": 1, "mrn": 0, "email": 1}
    assert original[0]["content"] == "전화 010-1234-5678"
    assert original[1]["content"][0]["text"] == "test.user@example.com"
