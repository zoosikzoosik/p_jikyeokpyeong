"""
즐겨찾기 화면.

is_bookmarked=True인 문제 목록을 표시하고,
"즐겨찾기만 풀기" 버튼으로 퀴즈 화면으로 이동할 수 있다.
"""
import streamlit as st

from components.auth import is_authenticated
from components.progress import get_bookmarks
from components.supabase_client import get_supabase_client

st.set_page_config(page_title="즐겨찾기", layout="wide")

# 사이드바 내비게이션
with st.sidebar:
    st.title("메뉴")
    st.page_link("app.py", label="메인")
    st.page_link("pages/1_quiz.py", label="문제 풀기")
    st.page_link("pages/2_wrong_notes.py", label="오답 노트")
    st.page_link("pages/4_progress.py", label="진도 현황")

if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

supabase = get_supabase_client()
user_id: str = st.session_state["user_id"]

st.title("즐겨찾기")

# ── 즐겨찾기 조회 ─────────────────────────────────────────────────────────
try:
    bookmarks = get_bookmarks(user_id, supabase)
except Exception as e:
    st.error(f"즐겨찾기를 불러올 수 없습니다: {e}")
    bookmarks = []

if not bookmarks:
    st.info("즐겨찾기한 문제가 없습니다.")
    st.stop()

# ── 문제 상세 정보 일괄 조회 ──────────────────────────────────────────────
question_ids = [b["question_id"] for b in bookmarks]
try:
    q_result = (
        supabase.table("questions")
        .select("id, content, type, answer, choices, explanation, part_id, parts(name)")
        .in_("id", question_ids)
        .execute()
    )
    questions_raw = q_result.data or []
except Exception as e:
    st.error(f"문제 정보를 불러올 수 없습니다: {e}")
    questions_raw = []

questions_by_id: dict[str, dict] = {q["id"]: q for q in questions_raw}

# ── 목록 표시 ─────────────────────────────────────────────────────────────
table_rows = []
for bm in bookmarks:
    q = questions_by_id.get(bm["question_id"])
    if q is None:
        continue
    part_name = (q.get("parts") or {}).get("name", "")
    q_type_label = {"ox": "OX", "fill": "빈칸", "mcq": "객관식"}.get(q["type"], q["type"])
    preview = q["content"][:60] + ("..." if len(q["content"]) > 60 else "")
    table_rows.append(
        {
            "파트명": part_name,
            "유형": q_type_label,
            "문제 미리보기": preview,
        }
    )

st.dataframe(table_rows, use_container_width=True)

# ── 즐겨찾기만 풀기 ───────────────────────────────────────────────────────
if st.button("즐겨찾기만 풀기"):
    quiz_questions = []
    for bm in bookmarks:
        q = questions_by_id.get(bm["question_id"])
        if q is None:
            continue
        clean_q = {k: v for k, v in q.items() if k != "parts"}
        quiz_questions.append(clean_q)

    if not quiz_questions:
        st.warning("풀 문제가 없습니다.")
    else:
        st.session_state["quiz_questions"] = quiz_questions
        st.session_state["quiz_index"] = 0
        st.session_state["quiz_answered"] = False
        st.session_state["quiz_feedback"] = None
        st.session_state.pop("selected_part_name", None)
        st.switch_page("pages/1_quiz.py")
