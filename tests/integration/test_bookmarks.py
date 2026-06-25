"""
AC5: 즐겨찾기 토글이 DB에 반영되고 즐겨찾기 목록에서 확인된다.

테스트 대상:
  - components.progress.toggle_bookmark(user_id, question_id, supabase) -> bool
      기존 is_bookmarked 값을 반전하여 저장하고 새 값을 반환한다.
  - components.progress.get_bookmarks(user_id, supabase) -> list[dict]
      is_bookmarked=True인 문제 목록을 반환한다.
"""
import pytest
from unittest.mock import MagicMock


class TestToggleBookmark:
    """즐겨찾기 토글: DB에 반전된 값이 저장된다."""

    def test_toggle_on_unbookmarked_question_returns_true(
        self, mock_supabase, user_id, question_id
    ):
        """북마크 안 된 문제를 토글하면 True(북마크 됨)가 반환된다."""
        from components.progress import toggle_bookmark

        existing_record = {
            "user_id": user_id,
            "question_id": question_id,
            "is_bookmarked": False,
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[existing_record]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{**existing_record, "is_bookmarked": True}]
        )

        result = toggle_bookmark(user_id, question_id, mock_supabase)

        assert result is True

    def test_toggle_on_bookmarked_question_returns_false(
        self, mock_supabase, user_id, question_id
    ):
        """북마크된 문제를 토글하면 False(북마크 해제됨)가 반환된다."""
        from components.progress import toggle_bookmark

        existing_record = {
            "user_id": user_id,
            "question_id": question_id,
            "is_bookmarked": True,
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[existing_record]
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{**existing_record, "is_bookmarked": False}]
        )

        result = toggle_bookmark(user_id, question_id, mock_supabase)

        assert result is False

    def test_toggle_calls_update_with_inverted_value(
        self, mock_supabase, user_id, question_id
    ):
        """update 호출 시 is_bookmarked 값이 반전되어야 한다."""
        from components.progress import toggle_bookmark

        existing_record = {
            "user_id": user_id,
            "question_id": question_id,
            "is_bookmarked": False,
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[existing_record]
        )
        updated_calls = []

        def capture_update(data):
            updated_calls.append(data)
            m = MagicMock()
            m.eq.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{**existing_record, **data}]
            )
            return m

        mock_supabase.table.return_value.update.side_effect = capture_update

        toggle_bookmark(user_id, question_id, mock_supabase)

        assert updated_calls, "update가 호출되지 않았다"
        assert updated_calls[0].get("is_bookmarked") is True, (
            "False → True로 반전되어 저장되어야 한다"
        )

    def test_toggle_creates_progress_record_if_not_exists(
        self, mock_supabase, user_id, question_id
    ):
        """user_progress 레코드가 없으면 is_bookmarked=True로 INSERT한다."""
        from components.progress import toggle_bookmark

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock(
            data=[{"user_id": user_id, "question_id": question_id, "is_bookmarked": True}]
        )

        result = toggle_bookmark(user_id, question_id, mock_supabase)

        assert result is True


class TestGetBookmarks:
    """즐겨찾기 목록 조회."""

    def test_returns_only_bookmarked_questions(self, mock_supabase, user_id, part_id):
        """is_bookmarked=True인 문제만 반환한다."""
        import uuid
        from components.progress import get_bookmarks

        bookmarked = [
            {"user_id": user_id, "question_id": str(uuid.uuid4()), "is_bookmarked": True},
            {"user_id": user_id, "question_id": str(uuid.uuid4()), "is_bookmarked": True},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=bookmarked
        )

        result = get_bookmarks(user_id, mock_supabase)

        assert len(result) == 2
        assert all(item["is_bookmarked"] is True for item in result)

    def test_returns_empty_list_when_no_bookmarks(self, mock_supabase, user_id):
        from components.progress import get_bookmarks

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = get_bookmarks(user_id, mock_supabase)

        assert result == []
