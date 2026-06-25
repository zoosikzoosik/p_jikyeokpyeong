"""
AC6: 오답 노트에서 wrong_count 내림차순으로 문제 목록이 표시된다.

테스트 대상:
  - components.progress.get_wrong_notes(user_id, supabase, part_id=None) -> list[dict]
      - wrong_count > 0인 레코드만 반환
      - wrong_count 내림차순 정렬
      - part_id 지정 시 해당 파트만 필터
"""
import uuid
import pytest
from unittest.mock import MagicMock


def _make_progress_row(user_id, wrong_count, q_part_id=None):
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "question_id": str(uuid.uuid4()),
        "wrong_count": wrong_count,
        "attempt_count": wrong_count + 1,
        "correct_count": 1,
        "is_bookmarked": False,
        "question": {"id": str(uuid.uuid4()), "part_id": q_part_id or str(uuid.uuid4())},
    }


class TestGetWrongNotes:
    """wrong_count > 0인 문제를 wrong_count 내림차순으로 반환한다."""

    def test_returns_questions_with_wrong_count_gt_zero(self, mock_supabase, user_id):
        from components.progress import get_wrong_notes

        rows_with_wrong = [
            _make_progress_row(user_id, wrong_count=3),
            _make_progress_row(user_id, wrong_count=1),
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gt.return_value.execute.return_value = MagicMock(
            data=rows_with_wrong
        )

        result = get_wrong_notes(user_id, mock_supabase)

        assert len(result) == 2
        assert all(item["wrong_count"] > 0 for item in result)

    def test_excludes_questions_with_zero_wrong_count(self, mock_supabase, user_id):
        """wrong_count=0인 문제는 오답 노트에 포함되지 않는다."""
        from components.progress import get_wrong_notes

        # mock이 wrong_count>0 필터를 적용하여 빈 리스트를 반환하는 경우를 시뮬레이션
        mock_supabase.table.return_value.select.return_value.eq.return_value.gt.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = get_wrong_notes(user_id, mock_supabase)

        assert result == []

    def test_sorted_by_wrong_count_descending(self, mock_supabase, user_id):
        """오답 노트는 wrong_count 내림차순으로 정렬되어야 한다."""
        from components.progress import get_wrong_notes

        # mock이 정렬되지 않은 순서로 데이터를 반환
        unsorted_rows = [
            _make_progress_row(user_id, wrong_count=2),
            _make_progress_row(user_id, wrong_count=5),
            _make_progress_row(user_id, wrong_count=1),
            _make_progress_row(user_id, wrong_count=3),
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gt.return_value.execute.return_value = MagicMock(
            data=unsorted_rows
        )

        result = get_wrong_notes(user_id, mock_supabase)

        wrong_counts = [item["wrong_count"] for item in result]
        assert wrong_counts == sorted(wrong_counts, reverse=True), (
            f"wrong_count가 내림차순이어야 하지만 실제 순서: {wrong_counts}"
        )

    def test_highest_wrong_count_is_first(self, mock_supabase, user_id):
        """가장 많이 틀린 문제가 첫 번째에 위치한다."""
        from components.progress import get_wrong_notes

        rows = [
            _make_progress_row(user_id, wrong_count=1),
            _make_progress_row(user_id, wrong_count=7),
            _make_progress_row(user_id, wrong_count=4),
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gt.return_value.execute.return_value = MagicMock(
            data=rows
        )

        result = get_wrong_notes(user_id, mock_supabase)

        assert result[0]["wrong_count"] == 7

    def test_part_filter_returns_only_that_part(self, user_id, part_id):
        """part_id를 지정하면 해당 파트의 오답만 반환한다."""
        from components.progress import get_wrong_notes

        target_row = _make_progress_row(user_id, wrong_count=3, q_part_id=part_id)
        target_row["question"]["part_id"] = part_id

        mock_supabase = MagicMock()
        # part_id 지정 시 DB 레벨 필터: .eq(user_id).gt().eq(questions.part_id).execute()
        mock_supabase.table.return_value.select.return_value.eq.return_value.gt.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[target_row]
        )

        result = get_wrong_notes(user_id, mock_supabase, part_id=part_id)

        assert len(result) == 1
        assert result[0]["question"]["part_id"] == part_id

    def test_returns_empty_when_no_wrong_answers(self, mock_supabase, user_id):
        """오답이 없으면 빈 리스트를 반환한다."""
        from components.progress import get_wrong_notes

        mock_supabase.table.return_value.select.return_value.eq.return_value.gt.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = get_wrong_notes(user_id, mock_supabase)

        assert result == []
