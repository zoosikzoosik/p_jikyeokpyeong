"""
문제 풀기 화면.

session_state["selected_part_id"] 기반으로 파트 문제를 로드하거나,
오답 노트/즐겨찾기에서 주입된 quiz_questions를 그대로 사용한다.

문제 유형:
  - ox  : O / X 버튼
  - fill: 텍스트 입력 + 제출 버튼
  - mcq : 라디오 4지선다 + 제출 버튼
"""
import random

import streamlit as st

from components.auth import is_authenticated
from components.progress import toggle_bookmark, upsert_progress
from components.question_card import check_answer, get_feedback
from components.supabase_client import get_supabase_client

st.set_page_config(page_title="문제 풀기", layout="centered")

# 사이드바 내비게이션
with st.sidebar:
    st.title("메뉴")
    st.page_link("app.py", label="메인")
    st.page_link("pages/2_wrong_notes.py", label="오답 노트")
    st.page_link("pages/3_bookmarks.py", label="즐겨찾기")
    st.page_link("pages/4_progress.py", label="진도 현황")

# 인증 확인
if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

supabase = get_supabase_client()
user_id: str = st.session_state["user_id"]


def _load_questions_for_part(part_id: str) -> list[dict]:
    """파트 ID로 문제를 조회하고 무작위로 섞어 반환한다."""
    result = (
        supabase.table("questions")
        .select("*")
        .eq("part_id", part_id)
        .execute()
    )
    questions = result.data or []
    random.shuffle(questions)
    return questions


def _init_quiz_from_part() -> None:
    """selected_part_id 기반으로 퀴즈 세션을 초기화한다."""
    if "selected_part_id" not in st.session_state:
        st.switch_page("app.py")
        st.stop()

    part_id: str = st.session_state["selected_part_id"]
    try:
        questions = _load_questions_for_part(part_id)
    except Exception as e:
        st.error(f"문제를 불러올 수 없습니다: {e}")
        st.stop()

    st.session_state["quiz_questions"] = questions
    st.session_state["quiz_index"] = 0
    st.session_state["quiz_answered"] = False
    st.session_state["quiz_feedback"] = None


# quiz_questions 없으면 파트에서 로드
if "quiz_questions" not in st.session_state:
    _init_quiz_from_part()

questions: list[dict] = st.session_state["quiz_questions"]

if not questions:
    st.warning("풀 문제가 없습니다.")
    if st.button("메인으로 돌아가기"):
        st.switch_page("app.py")
    st.stop()

quiz_index: int = st.session_state.get("quiz_index", 0)

# 모든 문제 완료
if quiz_index >= len(questions):
    st.success("모든 문제를 풀었습니다!")
    st.balloons()
    if st.button("메인으로 돌아가기"):
        for key in ["quiz_questions", "quiz_index", "quiz_answered", "quiz_feedback"]:
            st.session_state.pop(key, None)
        st.switch_page("app.py")
    st.stop()

question: dict = questions[quiz_index]
answered: bool = st.session_state.get("quiz_answered", False)

# ── 헤더 ───────────────────────────────────────────────────────────────────
part_name = st.session_state.get("selected_part_name", "문제 풀기")
st.subheader(f"{part_name} — {quiz_index + 1} / {len(questions)}")
st.progress((quiz_index) / len(questions))

# ── 즐겨찾기 토글 ─────────────────────────────────────────────────────────
bookmark_key = f"bookmark_{question['id']}"
is_bookmarked: bool = st.session_state.get(bookmark_key, False)
bookmark_label = "★ 즐겨찾기 해제" if is_bookmarked else "☆ 즐겨찾기"
if st.button(bookmark_label, key="bookmark_btn"):
    try:
        new_state = toggle_bookmark(user_id, question["id"], supabase)
        st.session_state[bookmark_key] = new_state
        st.rerun()
    except Exception as e:
        st.error(f"즐겨찾기 처리 중 오류: {e}")

# ── 문제 본문 ──────────────────────────────────────────────────────────────
st.markdown(f"**{question['content']}**")

# ── 입력 또는 피드백 ───────────────────────────────────────────────────────
if not answered:
    q_type: str = question["type"]

    if q_type == "ox":
        o_col, x_col = st.columns(2)
        with o_col:
            o_clicked = st.button("O", key="ox_o", use_container_width=True)
        with x_col:
            x_clicked = st.button("X", key="ox_x", use_container_width=True)

        user_answer = "O" if o_clicked else ("X" if x_clicked else None)
        if user_answer is not None:
            is_correct = check_answer(question, user_answer)
            try:
                upsert_progress(user_id, question["id"], is_correct, supabase)
            except Exception as e:
                st.error(f"진도 저장 중 오류: {e}")
            st.session_state["quiz_answered"] = True
            st.session_state["quiz_feedback"] = get_feedback(question, is_correct)
            st.rerun()

    elif q_type == "fill":
        user_answer = st.text_input("답을 입력하세요:", key="fill_input")
        if st.button("제출", key="fill_submit"):
            is_correct = check_answer(question, user_answer)
            try:
                upsert_progress(user_id, question["id"], is_correct, supabase)
            except Exception as e:
                st.error(f"진도 저장 중 오류: {e}")
            st.session_state["quiz_answered"] = True
            st.session_state["quiz_feedback"] = get_feedback(question, is_correct)
            st.rerun()

    elif q_type == "mcq":
        choices = question.get("choices") or []
        options = [f"{i + 1}. {c}" for i, c in enumerate(choices)]
        selected = st.radio("보기를 선택하세요:", options, key="mcq_radio", index=None)
        if st.button("제출", key="mcq_submit"):
            if selected is None:
                st.warning("보기를 선택해주세요.")
            else:
                choice_num = str(options.index(selected) + 1)
                is_correct = check_answer(question, choice_num)
                try:
                    upsert_progress(user_id, question["id"], is_correct, supabase)
                except Exception as e:
                    st.error(f"진도 저장 중 오류: {e}")
                st.session_state["quiz_answered"] = True
                st.session_state["quiz_feedback"] = get_feedback(question, is_correct)
                st.rerun()

else:
    # ── 피드백 표시 ────────────────────────────────────────────────────────
    feedback: dict = st.session_state["quiz_feedback"]
    if feedback["is_correct"]:
        st.success(feedback["message"])
    else:
        st.error(feedback["message"])

    explanation = feedback.get("explanation", "")
    if explanation:
        st.info(f"해설: {explanation}")

    # 다음 문제 또는 완료 버튼
    is_last = (quiz_index + 1 >= len(questions))
    next_label = "완료" if is_last else "다음 문제"
    if st.button(next_label, key="next_btn"):
        st.session_state["quiz_index"] = quiz_index + 1
        st.session_state["quiz_answered"] = False
        st.session_state["quiz_feedback"] = None
        st.rerun()
