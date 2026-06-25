"""
AC2: OX / 빈칸 / 4지선다 문제를 풀 수 있다.
AC3: 정답 제출 시 즉시 피드백과 해설이 표시된다.

테스트 대상:
  - components.question_card.check_answer(question, user_answer) -> bool
  - components.question_card.get_feedback(question, is_correct) -> dict
    반환 형태: {"is_correct": bool, "message": str, "explanation": str}
"""
import pytest


class TestCheckAnswerOX:
    """OX 문제 정답 판정."""

    def test_correct_o_answer(self, ox_question):
        from components.question_card import check_answer

        assert check_answer(ox_question, "O") is True

    def test_wrong_o_answered_as_x(self, ox_question):
        from components.question_card import check_answer

        assert check_answer(ox_question, "X") is False

    def test_correct_x_answer(self, part_id):
        from components.question_card import check_answer

        x_question = {
            "id": "some-id",
            "part_id": part_id,
            "type": "ox",
            "content": "리스크관리와 내부통제는 별개의 개념이다.",
            "answer": "X",
            "choices": None,
            "explanation": "리스크관리와 내부통제는 상호 보완적 개념이다.",
        }
        assert check_answer(x_question, "X") is True

    def test_wrong_x_answered_as_o(self, part_id):
        from components.question_card import check_answer

        x_question = {
            "id": "some-id",
            "part_id": part_id,
            "type": "ox",
            "content": "리스크관리와 내부통제는 별개의 개념이다.",
            "answer": "X",
            "choices": None,
            "explanation": "설명",
        }
        assert check_answer(x_question, "O") is False


class TestCheckAnswerFill:
    """빈칸 채우기: 완전 일치(trim + casefold)만 정답으로 인정."""

    def test_exact_match_is_correct(self, fill_question):
        from components.question_card import check_answer

        assert check_answer(fill_question, "시장") is True

    def test_leading_trailing_whitespace_is_correct(self, fill_question):
        """앞뒤 공백을 제거하면 정답이다 (trim)."""
        from components.question_card import check_answer

        assert check_answer(fill_question, "  시장  ") is True

    def test_case_insensitive_for_latin_characters(self, part_id):
        """영문 대소문자를 구분하지 않는다 (casefold)."""
        from components.question_card import check_answer

        english_fill = {
            "id": "some-id",
            "part_id": part_id,
            "type": "fill",
            "content": "리스크관리에서 VaR는 ___이다.",
            "answer": "value at risk",
            "choices": None,
            "explanation": "VaR = Value at Risk",
        }
        assert check_answer(english_fill, "VALUE AT RISK") is True
        assert check_answer(english_fill, "Value At Risk") is True

    def test_partial_match_is_wrong(self, fill_question):
        """부분 일치는 정답으로 인정하지 않는다."""
        from components.question_card import check_answer

        # fill_question의 정답은 "시장", "시장리스크"는 오답
        assert check_answer(fill_question, "시장리스크") is False

    def test_empty_answer_is_wrong(self, fill_question):
        from components.question_card import check_answer

        assert check_answer(fill_question, "") is False

    def test_wrong_answer(self, fill_question):
        from components.question_card import check_answer

        assert check_answer(fill_question, "신용") is False


class TestCheckAnswerMCQ:
    """4지선다 객관식: 선택지 번호('1'~'4') 비교."""

    def test_correct_choice_number(self, mcq_question):
        from components.question_card import check_answer

        # mcq_question의 정답은 "3"
        assert check_answer(mcq_question, "3") is True

    def test_wrong_choice_number(self, mcq_question):
        from components.question_card import check_answer

        assert check_answer(mcq_question, "1") is False
        assert check_answer(mcq_question, "2") is False
        assert check_answer(mcq_question, "4") is False


class TestGetFeedback:
    """정답/오답 피드백 및 해설 반환."""

    def test_correct_feedback_indicates_correct(self, ox_question):
        from components.question_card import get_feedback

        feedback = get_feedback(ox_question, is_correct=True)

        assert feedback["is_correct"] is True

    def test_wrong_feedback_indicates_wrong(self, ox_question):
        from components.question_card import get_feedback

        feedback = get_feedback(ox_question, is_correct=False)

        assert feedback["is_correct"] is False

    def test_feedback_includes_explanation(self, ox_question):
        """피드백에 해설이 포함되어야 한다."""
        from components.question_card import get_feedback

        feedback = get_feedback(ox_question, is_correct=True)

        assert "explanation" in feedback
        assert feedback["explanation"] == ox_question["explanation"]

    def test_feedback_has_message(self, ox_question):
        """피드백에 정답/오답 메시지가 포함되어야 한다."""
        from components.question_card import get_feedback

        correct_feedback = get_feedback(ox_question, is_correct=True)
        wrong_feedback = get_feedback(ox_question, is_correct=False)

        assert "message" in correct_feedback
        assert "message" in wrong_feedback
        # 정답과 오답의 메시지는 달라야 한다
        assert correct_feedback["message"] != wrong_feedback["message"]

    def test_feedback_includes_explanation_even_when_wrong(self, fill_question):
        """오답일 때도 해설을 표시한다."""
        from components.question_card import get_feedback

        feedback = get_feedback(fill_question, is_correct=False)

        assert feedback.get("explanation") == fill_question["explanation"]
