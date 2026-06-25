"""
직무역량평가 학습 앱 — 메인 진입점.

인증되지 않은 사용자에게는 로그인/회원가입 탭을 표시하고,
인증된 사용자에게는 파트 선택 메인 화면을 표시한다.
"""
import streamlit as st

from components.auth import is_authenticated, login, register
from components.progress import get_progress_dashboard
from components.supabase_client import get_supabase_client

st.set_page_config(page_title="직무역량평가 학습앱", layout="wide")


def _show_auth_screen(supabase) -> None:
    st.title("직무역량평가 학습앱")
    login_tab, register_tab = st.tabs(["로그인", "회원가입"])

    with login_tab:
        nickname = st.text_input("닉네임", key="login_nickname")
        password = st.text_input("비밀번호", type="password", key="login_password")
        if st.button("로그인", key="login_btn"):
            user = login(nickname, password, supabase)
            if user:
                st.session_state["user_id"] = user["id"]
                st.session_state["nickname"] = user["nickname"]
                st.rerun()
            else:
                st.error("닉네임 또는 비밀번호가 올바르지 않습니다.")

    with register_tab:
        reg_nickname = st.text_input("닉네임", key="register_nickname")
        reg_password = st.text_input("비밀번호", type="password", key="register_password")
        if st.button("회원가입", key="register_btn"):
            try:
                user = register(reg_nickname, reg_password, supabase)
                st.session_state["user_id"] = user["id"]
                st.session_state["nickname"] = user["nickname"]
                st.rerun()
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"회원가입 중 오류가 발생했습니다: {e}")


def _show_main_screen(supabase) -> None:
    user_id: str = st.session_state["user_id"]
    nickname: str = st.session_state["nickname"]

    # 사이드바 내비게이션
    with st.sidebar:
        st.title("메뉴")
        st.page_link("pages/2_wrong_notes.py", label="오답 노트")
        st.page_link("pages/3_bookmarks.py", label="즐겨찾기")
        st.page_link("pages/4_progress.py", label="진도 현황")

    # 헤더 행
    header_col, logout_col = st.columns([8, 1])
    with header_col:
        st.header(f"안녕하세요, {nickname}님")
    with logout_col:
        st.write("")  # 버튼 수직 정렬용 여백
        if st.button("로그아웃"):
            st.session_state.clear()
            st.rerun()

    st.subheader("파트 선택")

    # 진도 대시보드 조회
    try:
        dashboard = get_progress_dashboard(user_id, supabase)
    except Exception as e:
        st.error(f"진도 정보를 불러올 수 없습니다: {e}")
        dashboard = []

    if not dashboard:
        st.info("등록된 파트가 없습니다. 관리자에게 문의하세요.")
        return

    # 3열 그리드로 파트 카드 표시
    cols = st.columns(3)
    for idx, part in enumerate(dashboard):
        with cols[idx % 3]:
            attempted = part["attempted_count"]
            total = part["total_questions"]
            accuracy = part["accuracy"]
            summary = f"{attempted}/{total} 풀음 · 정답률 {accuracy:.0f}%"

            with st.container(border=True):
                st.markdown(f"**{part['part_name']}**")
                st.caption(summary)
                if st.button("풀기", key=f"part_{part['part_id']}"):
                    # 파트 이동 시 이전 퀴즈 상태 초기화
                    for key in ["quiz_questions", "quiz_index", "quiz_answered", "quiz_feedback"]:
                        st.session_state.pop(key, None)
                    st.session_state["selected_part_id"] = part["part_id"]
                    st.session_state["selected_part_name"] = part["part_name"]
                    st.switch_page("pages/1_quiz.py")


def main() -> None:
    supabase = get_supabase_client()

    if not is_authenticated():
        _show_auth_screen(supabase)
    else:
        _show_main_screen(supabase)


main()
