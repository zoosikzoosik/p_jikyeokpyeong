"""
Supabase 클라이언트 초기화.

Streamlit secrets에서 URL과 KEY를 읽어 클라이언트를 생성한다.
테스트 시에는 mock 클라이언트를 직접 주입(DI)하므로 이 모듈을 호출하지 않는다.
"""
import streamlit as st


def get_supabase_client():
    """
    Supabase 클라이언트를 반환한다.

    .streamlit/secrets.toml에 아래 항목이 필요하다:
        SUPABASE_URL = "https://..."
        SUPABASE_KEY = "eyJ..."
    """
    from supabase import create_client

    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
