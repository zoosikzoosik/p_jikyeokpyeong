"""
오답 노트 화면.

wrong_count > 0인 문제 목록을 파트 필터와 함께 표시하고,
"오답만 풀기" 버튼으로 퀴즈 화면으로 이동할 수 있다.
"""
import streamlit as st

from components.auth import is_authenticated
from components.progress import get_wrong_notes
from components.supabase_client import get_supabase_client

st.set_page_config(page_title="오답 노트", layout="wide")

# 사이드바 내비게이션
with st.sidebar:
    st.title("메뉴")
    st.page_link("app.py", label="메인")
    st.page_link("pages/1_quiz.py", label="문제 풀기")
    st.page_link("pages/3_bookmarks.py", label="즐겨찾기")
    st.page_link("pages/4_progress.py", label="진도 현황")

if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

supabase = get_supabase_client()
user_id: str = st.session_state["user_id"]

st.title("오답 노트")

# ── 파트 목록 조회 (필터용) ────────────────────────────────────────────────
try:
    parts_result = supabase.table("parts").select("*").order("order_num").execute()
    parts = parts_result.data or []
except Exception as e:
    st.error(f"파트 목록을 불러올 수 없습니다: {e}")
    parts = []

part_options = {"전체": None}
for p in parts:
    part_options[p["name"]] = p["id"]

selected_part_label = st.selectbox("파트 필터", options=list(part_options.keys()))
selected_part_id = part_options[selected_part_label]

# ── 오답 노트 조회 ─────────────────────────────────────────────────────────
try:
    wrong_notes = get_wrong_notes(user_id, supabase, part_id=selected_part_id)
except Exception as e:
    st.error(f"오답 노트를 불러올 수 없습니다: {e}")
    wrong_notes = []

if not wrong_notes:
    st.info("오답 기록이 없습니다.")
    st.stop()

# ── 문제 상세 정보 일괄 조회 ──────────────────────────────────────────────
question_ids = [n["question_id"] for n in wrong_notes]
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

# ── 테이블 표시 ───────────────────────────────────────────────────────────
table_rows = []
for note in wrong_notes:
    q = questions_by_id.get(note["question_id"])
    if q is None:
        continue
    part_name = (q.get("parts") or {}).get("name", "")
    preview = q["content"][:60] + ("..." if len(q["content"]) > 60 else "")
    table_rows.append(
        {
            "파트명": part_name,
            "문제 미리보기": preview,
            "틀린 횟수": note["wrong_count"],
        }
    )

st.dataframe(table_rows, use_container_width=True)

# ── 오답만 풀기 ───────────────────────────────────────────────────────────
if st.button("오답만 풀기"):
    # 오답 문제 객체만 추출 (questions join 필드 제거)
    quiz_questions = []
    for note in wrong_notes:
        q = questions_by_id.get(note["question_id"])
        if q is None:
            continue
        # parts 조인 필드 제거 후 저장
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
