"""
AC1: 비밀번호 없이는 앱에 접근할 수 없다.

테스트 대상:
  - components.auth.login(nickname, password, supabase) -> dict | None
  - components.auth.register(nickname, password, supabase) -> dict
  - components.auth.is_authenticated() -> bool  (st.session_state 확인)
"""
import bcrypt
import pytest
from unittest.mock import MagicMock, patch


class TestLogin:
    """올바른 자격증명만 로그인을 허용한다."""

    def test_valid_credentials_return_user(self, mock_supabase, sample_user):
        from components.auth import login

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_user]
        )

        result = login("테스트유저", "testpass123", mock_supabase)

        assert result is not None
        assert result["id"] == sample_user["id"]
        assert result["nickname"] == "테스트유저"

    def test_wrong_password_returns_none(self, mock_supabase, sample_user):
        from components.auth import login

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_user]
        )

        result = login("테스트유저", "wrongpassword", mock_supabase)

        assert result is None

    def test_nonexistent_user_returns_none(self, mock_supabase):
        from components.auth import login

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = login("존재하지않는유저", "anypassword", mock_supabase)

        assert result is None

    def test_empty_password_returns_none(self, mock_supabase, sample_user):
        """빈 비밀번호로는 로그인할 수 없다."""
        from components.auth import login

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_user]
        )

        result = login("테스트유저", "", mock_supabase)

        assert result is None

    def test_empty_nickname_returns_none(self, mock_supabase):
        """빈 닉네임으로는 로그인할 수 없다."""
        from components.auth import login

        result = login("", "somepassword", mock_supabase)

        assert result is None


class TestRegister:
    """신규 사용자 등록 시 bcrypt 해시로 비밀번호를 저장한다."""

    def test_register_new_user_returns_user_dict(self, mock_supabase):
        from components.auth import register

        new_user = {"id": str(__import__("uuid").uuid4()), "nickname": "신규유저", "password_hash": "hashed"}
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[new_user]
        )

        result = register("신규유저", "mypassword", mock_supabase)

        assert result is not None
        assert result["nickname"] == "신규유저"

    def test_register_stores_bcrypt_hash_not_plaintext(self, mock_supabase):
        """비밀번호는 평문이 아닌 bcrypt 해시로 저장되어야 한다."""
        from components.auth import register

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        inserted = []

        def capture_insert(data):
            row = data[0] if isinstance(data, list) else data
            inserted.append(row)
            m = MagicMock()
            m.execute.return_value = MagicMock(data=[row])
            return m

        mock_supabase.table.return_value.insert.side_effect = capture_insert

        register("신규유저", "mypassword", mock_supabase)

        assert inserted, "insert가 호출되지 않았다"
        stored_hash = inserted[0]["password_hash"]
        assert stored_hash != "mypassword", "비밀번호가 평문으로 저장되었다"
        assert bcrypt.checkpw(b"mypassword", stored_hash.encode()), "저장된 해시가 원본 비밀번호와 일치하지 않는다"

    def test_register_raises_on_duplicate_nickname(self, mock_supabase, sample_user):
        """이미 존재하는 닉네임으로 가입을 시도하면 예외가 발생한다."""
        from components.auth import register

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[sample_user]
        )

        with pytest.raises(Exception):
            register("테스트유저", "password", mock_supabase)


class TestIsAuthenticated:
    """세션에 user_id가 없으면 인증되지 않은 상태다."""

    def test_returns_false_without_user_in_session(self):
        from components.auth import is_authenticated

        with patch("components.auth.st") as mock_st:
            mock_st.session_state = {}
            result = is_authenticated()

        assert result is False

    def test_returns_true_with_user_id_in_session(self):
        from components.auth import is_authenticated

        with patch("components.auth.st") as mock_st:
            mock_st.session_state = {"user_id": "some-uuid-value"}
            result = is_authenticated()

        assert result is True
