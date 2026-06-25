"""
AC4: 문제 제출 시 user_progress를 UPSERT한다.
     동일 문제를 3회 풀어 2회 정답이면 attempt_count=3, correct_count=2, wrong_count=1.

테스트 대상:
  - components.progress.upsert_progress(user_id, question_id, is_correct, supabase) -> dict

UPSERT 규칙:
  - 레코드 없으면 INSERT (attempt_count=1, correct_count or wrong_count = 1)
  - 레코드 있으면 UPDATE (attempt_count +1, 정답이면 correct_count +1, 오답이면 wrong_count +1)
  - last_attempted_at, last_correct 갱신
"""
import pytest
from unittest.mock import MagicMock, call


def _make_stateful_progress_mock(user_id: str, question_id: str):
    """
    user_progress 테이블의 select/upsert를 in-memory dict로 시뮬레이션하는 mock.
    반환: (mock_supabase, progress_store)
      - progress_store[(user_id, question_id)] 에서 최종 상태를 확인한다.
    """
    progress_store = {}

    def table_dispatch(table_name):
        t = MagicMock()
        if table_name == "user_progress":
            # SELECT: .select("*").eq("user_id", ...).eq("question_id", ...).execute()
            def select_chain(*args, **kwargs):
                s = MagicMock()

                def eq_user(col, uid):
                    e1 = MagicMock()

                    def eq_question(col2, qid):
                        e2 = MagicMock()
                        key = (uid, qid)
                        e2.execute.return_value = MagicMock(
                            data=[progress_store[key]] if key in progress_store else []
                        )
                        return e2

                    e1.eq = eq_question
                    return e1

                s.eq = eq_user
                return s

            t.select = select_chain

            # UPSERT: .upsert({...}, on_conflict="...").execute()
            def upsert_chain(data, **kwargs):
                row = data[0] if isinstance(data, list) else data
                key = (row["user_id"], row["question_id"])
                progress_store[key] = row
                u = MagicMock()
                u.execute.return_value = MagicMock(data=[row])
                return u

            t.upsert = upsert_chain
        return t

    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = table_dispatch
    return mock_supabase, progress_store


class TestUpsertProgressInsert:
    """첫 번째 시도 — INSERT(attempt_count=1)."""

    def test_first_correct_attempt_creates_record(self, user_id, question_id):
        from components.progress import upsert_progress

        mock_supabase, store = _make_stateful_progress_mock(user_id, question_id)

        upsert_progress(user_id, question_id, is_correct=True, supabase=mock_supabase)

        key = (user_id, question_id)
        assert key in store, "user_progress 레코드가 생성되지 않았다"
        assert store[key]["attempt_count"] == 1
        assert store[key]["correct_count"] == 1
        assert store[key]["wrong_count"] == 0

    def test_first_wrong_attempt_creates_record(self, user_id, question_id):
        from components.progress import upsert_progress

        mock_supabase, store = _make_stateful_progress_mock(user_id, question_id)

        upsert_progress(user_id, question_id, is_correct=False, supabase=mock_supabase)

        key = (user_id, question_id)
        assert key in store
        assert store[key]["attempt_count"] == 1
        assert store[key]["correct_count"] == 0
        assert store[key]["wrong_count"] == 1


class TestUpsertProgressUpdate:
    """기존 레코드 업데이트 — attempt_count 누적."""

    def test_correct_attempt_increments_correct_count(self, user_id, question_id):
        from components.progress import upsert_progress

        mock_supabase, store = _make_stateful_progress_mock(user_id, question_id)

        upsert_progress(user_id, question_id, is_correct=True, supabase=mock_supabase)
        upsert_progress(user_id, question_id, is_correct=True, supabase=mock_supabase)

        key = (user_id, question_id)
        assert store[key]["attempt_count"] == 2
        assert store[key]["correct_count"] == 2
        assert store[key]["wrong_count"] == 0

    def test_wrong_attempt_increments_wrong_count(self, user_id, question_id):
        from components.progress import upsert_progress

        mock_supabase, store = _make_stateful_progress_mock(user_id, question_id)

        upsert_progress(user_id, question_id, is_correct=True, supabase=mock_supabase)
        upsert_progress(user_id, question_id, is_correct=False, supabase=mock_supabase)

        key = (user_id, question_id)
        assert store[key]["attempt_count"] == 2
        assert store[key]["correct_count"] == 1
        assert store[key]["wrong_count"] == 1


class TestUpsertProgressThreeAttempts:
    """AC4 핵심 검증: 3회 풀어 2회 정답 → attempt=3, correct=2, wrong=1."""

    def test_three_attempts_two_correct_one_wrong(self, user_id, question_id):
        from components.progress import upsert_progress

        mock_supabase, store = _make_stateful_progress_mock(user_id, question_id)

        # 1회차: 정답
        upsert_progress(user_id, question_id, is_correct=True, supabase=mock_supabase)
        # 2회차: 오답
        upsert_progress(user_id, question_id, is_correct=False, supabase=mock_supabase)
        # 3회차: 정답
        upsert_progress(user_id, question_id, is_correct=True, supabase=mock_supabase)

        key = (user_id, question_id)
        assert store[key]["attempt_count"] == 3, f"attempt_count 기대값=3, 실제={store[key]['attempt_count']}"
        assert store[key]["correct_count"] == 2, f"correct_count 기대값=2, 실제={store[key]['correct_count']}"
        assert store[key]["wrong_count"] == 1, f"wrong_count 기대값=1, 실제={store[key]['wrong_count']}"

    def test_last_correct_updated_per_attempt(self, user_id, question_id):
        """last_correct는 가장 최근 시도의 정오 여부를 반영한다."""
        from components.progress import upsert_progress

        mock_supabase, store = _make_stateful_progress_mock(user_id, question_id)

        upsert_progress(user_id, question_id, is_correct=True, supabase=mock_supabase)
        upsert_progress(user_id, question_id, is_correct=False, supabase=mock_supabase)

        key = (user_id, question_id)
        assert store[key]["last_correct"] is False, "마지막 시도가 오답이면 last_correct는 False여야 한다"

    def test_last_attempted_at_is_set(self, user_id, question_id):
        """last_attempted_at이 None이 아닌 값으로 기록된다."""
        from components.progress import upsert_progress

        mock_supabase, store = _make_stateful_progress_mock(user_id, question_id)

        upsert_progress(user_id, question_id, is_correct=True, supabase=mock_supabase)

        key = (user_id, question_id)
        assert store[key].get("last_attempted_at") is not None
