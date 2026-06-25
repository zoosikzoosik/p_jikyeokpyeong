"""
문제 카드 컴포넌트.

check_answer(): 문제 유형별 정답 판정
get_feedback(): 정답/오답 피드백 + 해설 반환
"""


def check_answer(question: dict, user_answer: str) -> bool:
    """
    문제 유형에 따라 정답 여부를 판정한다.

    - ox  : 'O' 또는 'X' 완전 일치
    - fill: 앞뒤 공백 제거(strip) + casefold 완전 일치, 빈 답안은 오답
    - mcq : '1'~'4' 완전 일치
    """
    q_type = question["type"]
    correct = question["answer"]

    if q_type == "ox":
        return user_answer == correct

    if q_type == "fill":
        if not user_answer:
            return False
        return user_answer.strip().casefold() == correct.strip().casefold()

    if q_type == "mcq":
        return user_answer == correct

    return False


def get_feedback(question: dict, is_correct: bool) -> dict:
    """
    정답/오답 여부와 해설을 담은 피드백 dict를 반환한다.

    Returns:
        {
            "is_correct": bool,
            "message": str,       # 정답/오답에 따라 다른 메시지
            "explanation": str,
        }
    """
    message = "정답입니다!" if is_correct else "오답입니다."
    return {
        "is_correct": is_correct,
        "message": message,
        "explanation": question.get("explanation", ""),
    }
