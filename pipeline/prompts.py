"""
LLM 프롬프트 템플릿 모음.

OCR 파이프라인에서 사용하는 프롬프트를 관리한다.
"""


OCR_PROMPT = "이미지의 텍스트를 그대로 추출해주세요. 레이아웃이나 형식 설명 없이 순수 텍스트만 반환하세요."


def make_question_generation_prompt(text: str, question_count: int = 10) -> str:
    """
    추출된 텍스트를 기반으로 문제 생성을 요청하는 프롬프트를 반환한다.

    응답 형식은 JSON이며 아래 구조를 따른다:
    {
        "ox": [{"content": str, "answer": "O"|"X", "explanation": str}, ...],
        "fill": [{"content": str, "answer": str, "explanation": str}, ...],
        "mcq": [{"content": str, "answer": "1"|"2"|"3"|"4",
                 "choices": [str, str, str, str], "explanation": str}, ...]
    }
    """
    return f"""다음 학습 자료를 바탕으로 문제를 생성해주세요.

[학습 자료]
{text}

아래 형식의 JSON만 반환하세요 (마크다운 없이):
{{
  "ox": [
    {{"content": "문제 내용", "answer": "O", "explanation": "해설"}}
  ],
  "fill": [
    {{"content": "빈칸이 포함된 ___ 문제", "answer": "정답", "explanation": "해설"}}
  ],
  "mcq": [
    {{
      "content": "문제 내용",
      "answer": "3",
      "choices": ["보기1", "보기2", "보기3", "보기4"],
      "explanation": "해설"
    }}
  ]
}}

각 유형별로 {question_count}개씩 생성해주세요.
- OX 문제: answer는 "O" 또는 "X"
- 빈칸 문제: content에 ___로 빈칸 표시, answer는 빈칸에 들어갈 단어
- 객관식: answer는 정답 번호 문자열 ("1"~"4")
"""
