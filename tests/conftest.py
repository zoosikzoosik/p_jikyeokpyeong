"""
공유 픽스처 및 전역 설정.

Streamlit이 테스트 환경에서 import될 때 서버를 띄우지 않도록
sys.modules에 MagicMock을 미리 등록한다.
"""
import sys
import uuid
from unittest.mock import MagicMock

import bcrypt
import pytest

# Streamlit을 테스트 환경에서 mock 처리 (서버 없이 import 가능)
sys.modules.setdefault("streamlit", MagicMock())


# ---------------------------------------------------------------------------
# 기본 ID 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


@pytest.fixture
def part_id():
    return str(uuid.uuid4())


@pytest.fixture
def question_id():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# 도메인 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_part(part_id):
    return {"id": part_id, "name": "리스크관리", "order_num": 1}


@pytest.fixture
def ox_question(part_id):
    return {
        "id": str(uuid.uuid4()),
        "part_id": part_id,
        "type": "ox",
        "content": "신용리스크는 거래 상대방의 채무불이행으로 인한 손실 위험이다.",
        "answer": "O",
        "choices": None,
        "explanation": "신용리스크 기본 정의: 거래 상대방이 계약 의무를 이행하지 않아 발생하는 손실 위험",
    }


@pytest.fixture
def fill_question(part_id):
    return {
        "id": str(uuid.uuid4()),
        "part_id": part_id,
        "type": "fill",
        "content": "VaR는 ___ 위험가치 측정 방법이다.",
        "answer": "시장",
        "choices": None,
        "explanation": "Value at Risk(VaR)는 시장 위험을 정량화하는 대표적 도구이다.",
    }


@pytest.fixture
def mcq_question(part_id):
    return {
        "id": str(uuid.uuid4()),
        "part_id": part_id,
        "type": "mcq",
        "content": "다음 중 신용리스크 경감 기법이 아닌 것은?",
        "answer": "3",
        "choices": ["담보", "보증", "투기", "네팅"],
        "explanation": "신용리스크 경감 기법: 담보, 보증, 네팅 등. '투기'는 경감 기법이 아니다.",
    }


@pytest.fixture
def hashed_password():
    """bcrypt 해시 비밀번호 (원문: testpass123)"""
    return bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode()


@pytest.fixture
def sample_user(hashed_password):
    return {
        "id": str(uuid.uuid4()),
        "nickname": "테스트유저",
        "password_hash": hashed_password,
    }


@pytest.fixture
def sample_progress(user_id, question_id):
    """user_progress 테이블 레코드 예시"""
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "question_id": question_id,
        "attempt_count": 1,
        "wrong_count": 0,
        "correct_count": 1,
        "is_bookmarked": False,
        "last_attempted_at": "2026-06-26T00:00:00Z",
        "last_correct": True,
    }


# ---------------------------------------------------------------------------
# Mock 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_supabase():
    """범용 Supabase mock — 테스트마다 개별 설정이 필요하다."""
    return MagicMock()


@pytest.fixture
def mock_anthropic():
    """Claude API mock"""
    return MagicMock()


# ---------------------------------------------------------------------------
# 헬퍼: 테이블별 응답을 분기하는 Supabase mock
# ---------------------------------------------------------------------------


def make_table_router(table_responses: dict) -> MagicMock:
    """
    table_responses: {"tablename": mock_table_object, ...}
    반환된 mock의 .table(name) 호출을 딕셔너리로 라우팅한다.
    """
    base = MagicMock()
    base.table.side_effect = lambda name: table_responses.get(name, MagicMock())
    return base
