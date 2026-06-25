"""
AC7: 진도 현황에서 파트별 풀어본 문제 수와 정답률이 표시된다.
     정답률 계산식: correct_count / attempt_count × 100

테스트 대상:
  - components.progress.get_progress_dashboard(user_id, supabase) -> list[dict]
      반환 형태: [
          {
              "part_id": str,
              "part_name": str,
              "total_questions": int,        # 파트 전체 문제 수
              "attempted_count": int,        # 풀어본 문제 수 (attempt_count > 0)
              "accuracy": float,             # correct_count / attempt_count × 100
          },
          ...
      ]
"""
import uuid
import pytest
from unittest.mock import MagicMock


def _make_part(name, order_num):
    return {"id": str(uuid.uuid4()), "name": name, "order_num": order_num}


def _make_progress_row(user_id, question_id, attempt_count, correct_count, wrong_count):
    return {
        "user_id": user_id,
        "question_id": question_id,
        "attempt_count": attempt_count,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
    }


class TestGetProgressDashboard:
    """파트별 정답률 및 진도 현황 계산."""

    def test_accuracy_is_correct_count_over_attempt_count_times_100(
        self, mock_supabase, user_id, part_id
    ):
        """정답률 = correct_count / attempt_count × 100."""
        from components.progress import get_progress_dashboard

        q_id = str(uuid.uuid4())
        progress_rows = [
            _make_progress_row(user_id, q_id, attempt_count=4, correct_count=3, wrong_count=1)
        ]
        parts = [{"id": part_id, "name": "리스크관리", "order_num": 1}]
        questions = [{"id": q_id, "part_id": part_id}]

        mock_supabase.table.side_effect = _build_dashboard_table_mock(
            parts, questions, progress_rows, user_id
        )

        result = get_progress_dashboard(user_id, mock_supabase)

        part_row = next(r for r in result if r["part_id"] == part_id)
        expected_accuracy = 3 / 4 * 100  # 75.0
        assert abs(part_row["accuracy"] - expected_accuracy) < 0.01, (
            f"정답률 기대값={expected_accuracy}, 실제={part_row['accuracy']}"
        )

    def test_no_division_by_zero_when_not_attempted(
        self, mock_supabase, user_id, part_id
    ):
        """attempt_count=0인 경우 ZeroDivisionError 없이 0.0을 반환한다."""
        from components.progress import get_progress_dashboard

        parts = [{"id": part_id, "name": "금융상품", "order_num": 2}]
        questions = [{"id": str(uuid.uuid4()), "part_id": part_id}]
        progress_rows = []  # 아직 한 번도 풀지 않음

        mock_supabase.table.side_effect = _build_dashboard_table_mock(
            parts, questions, progress_rows, user_id
        )

        result = get_progress_dashboard(user_id, mock_supabase)

        part_row = next((r for r in result if r["part_id"] == part_id), None)
        assert part_row is not None
        assert part_row["accuracy"] == 0.0
        assert part_row["attempted_count"] == 0

    def test_attempted_count_counts_only_attempted_questions(
        self, mock_supabase, user_id, part_id
    ):
        """풀어본 문제 수는 attempt_count > 0인 문제의 수다."""
        from components.progress import get_progress_dashboard

        q1 = str(uuid.uuid4())
        q2 = str(uuid.uuid4())
        q3 = str(uuid.uuid4())  # 아직 풀지 않음
        parts = [{"id": part_id, "name": "리스크관리", "order_num": 1}]
        questions = [
            {"id": q1, "part_id": part_id},
            {"id": q2, "part_id": part_id},
            {"id": q3, "part_id": part_id},
        ]
        progress_rows = [
            _make_progress_row(user_id, q1, attempt_count=2, correct_count=1, wrong_count=1),
            _make_progress_row(user_id, q2, attempt_count=1, correct_count=1, wrong_count=0),
        ]

        mock_supabase.table.side_effect = _build_dashboard_table_mock(
            parts, questions, progress_rows, user_id
        )

        result = get_progress_dashboard(user_id, mock_supabase)

        part_row = next(r for r in result if r["part_id"] == part_id)
        assert part_row["total_questions"] == 3
        assert part_row["attempted_count"] == 2

    def test_includes_all_parts_even_with_no_progress(
        self, mock_supabase, user_id
    ):
        """풀지 않은 파트도 결과에 포함된다 (attempted=0, accuracy=0.0)."""
        from components.progress import get_progress_dashboard

        part_a = _make_part("리스크관리", 1)
        part_b = _make_part("금융상품", 2)
        parts = [part_a, part_b]
        q_a = str(uuid.uuid4())
        questions = [{"id": q_a, "part_id": part_a["id"]}]
        progress_rows = [
            _make_progress_row(user_id, q_a, attempt_count=1, correct_count=1, wrong_count=0)
        ]

        mock_supabase.table.side_effect = _build_dashboard_table_mock(
            parts, questions, progress_rows, user_id
        )

        result = get_progress_dashboard(user_id, mock_supabase)

        part_ids = [r["part_id"] for r in result]
        assert part_b["id"] in part_ids, "풀지 않은 파트도 목록에 포함되어야 한다"

    def test_perfect_score_accuracy_is_100(self, mock_supabase, user_id, part_id):
        from components.progress import get_progress_dashboard

        q_id = str(uuid.uuid4())
        parts = [{"id": part_id, "name": "리스크관리", "order_num": 1}]
        questions = [{"id": q_id, "part_id": part_id}]
        progress_rows = [
            _make_progress_row(user_id, q_id, attempt_count=3, correct_count=3, wrong_count=0)
        ]

        mock_supabase.table.side_effect = _build_dashboard_table_mock(
            parts, questions, progress_rows, user_id
        )

        result = get_progress_dashboard(user_id, mock_supabase)

        part_row = next(r for r in result if r["part_id"] == part_id)
        assert part_row["accuracy"] == 100.0


def _build_dashboard_table_mock(parts, questions, progress_rows, user_id):
    """
    get_progress_dashboard가 사용하는 테이블 조회를 시뮬레이션하는 팩토리.
    테이블별로 다른 응답을 반환한다.
    """

    def dispatch(table_name):
        t = MagicMock()
        if table_name == "parts":
            t.select.return_value.order.return_value.execute.return_value = MagicMock(data=parts)
            t.select.return_value.execute.return_value = MagicMock(data=parts)
        elif table_name == "questions":
            t.select.return_value.execute.return_value = MagicMock(data=questions)
            t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=questions)
        elif table_name == "user_progress":
            t.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=progress_rows
            )
        return t

    return dispatch
