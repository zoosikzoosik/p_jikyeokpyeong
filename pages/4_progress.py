"""
진도 현황 화면.

파트별 전체 문제 수, 풀어본 문제 수, 정답률(%)을 테이블로 표시한다.
마지막 행에는 전체 합계/평균을 표시한다.
"""
import streamlit as st

from components.auth import is_authenticated
from components.progress import get_progress_dashboard
from components.supabase_client import get_supabase_client

st.set_page_config(page_title="진도 현황", layout="wide")

# 사이드바 내비게이션
with st.sidebar:
    st.title("메뉴")
    st.page_link("app.py", label="메인")
    st.page_link("pages/1_quiz.py", label="문제 풀기")
    st.page_link("pages/2_wrong_notes.py", label="오답 노트")
    st.page_link("pages/3_bookmarks.py", label="즐겨찾기")

if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

supabase = get_supabase_client()
user_id: str = st.session_state["user_id"]

st.title("진도 현황")

# ── 대시보드 조회 ─────────────────────────────────────────────────────────
try:
    dashboard = get_progress_dashboard(user_id, supabase)
except Exception as e:
    st.error(f"진도 정보를 불러올 수 없습니다: {e}")
    dashboard = []

if not dashboard:
    st.info("아직 풀어본 문제가 없습니다.")
    st.stop()

# ── 테이블 데이터 구성 ────────────────────────────────────────────────────
rows = []
for d in dashboard:
    rows.append(
        {
            "파트명": d["part_name"],
            "전체 문제 수": d["total_questions"],
            "풀어본 문제": d["attempted_count"],
            "정답률(%)": round(d["accuracy"], 1),
        }
    )

# 전체 합계 행
total_questions = sum(d["total_questions"] for d in dashboard)
total_attempted = sum(d["attempted_count"] for d in dashboard)

# 정답률 전체 가중 평균 (풀어본 문제 수 기준)
total_accuracy = (
    sum(d["accuracy"] * d["attempted_count"] for d in dashboard) / total_attempted
    if total_attempted > 0
    else 0.0
)

rows.append(
    {
        "파트명": "전체",
        "전체 문제 수": total_questions,
        "풀어본 문제": total_attempted,
        "정답률(%)": round(total_accuracy, 1),
    }
)

st.dataframe(rows, use_container_width=True)
