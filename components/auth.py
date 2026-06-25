"""
인증 모듈: 닉네임 + bcrypt 비밀번호 기반 로그인/회원가입.

login(), register(), is_authenticated() 세 함수를 제공한다.
supabase 클라이언트는 의존성 주입(파라미터)으로 받으므로 테스트 용이하다.
"""
import bcrypt
import streamlit as st


def login(nickname: str, password: str, supabase) -> dict | None:
    """
    닉네임 + 비밀번호로 로그인한다.

    Returns:
        사용자 dict(id, nickname, ...) — 인증 성공
        None — 닉네임 없음, 비밀번호 불일치, 빈 입력
    """
    if not nickname or not password:
        return None

    result = supabase.table("users").select("*").eq("nickname", nickname).execute()

    if not result.data:
        return None

    user = result.data[0]

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return None

    return user


def register(nickname: str, password: str, supabase) -> dict:
    """
    신규 사용자를 등록한다. 비밀번호는 bcrypt 해시로 저장한다.

    Raises:
        ValueError: 닉네임이 이미 존재하는 경우
    """
    existing = supabase.table("users").select("*").eq("nickname", nickname).execute()

    if existing.data:
        raise ValueError("이미 사용 중인 닉네임입니다")

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    new_user = {
        "nickname": nickname,
        "password_hash": password_hash,
    }

    try:
        result = supabase.table("users").insert([new_user]).execute()
    except Exception as e:
        if "23505" in str(e) or "unique" in str(e).lower():
            raise ValueError("이미 사용 중인 닉네임입니다") from e
        raise
    return result.data[0]


def is_authenticated() -> bool:
    """세션에 user_id가 저장되어 있으면 인증된 상태로 간주한다."""
    return "user_id" in st.session_state
