"""
OCR + 문제 자동 생성 파이프라인 스크립트.

run_pipeline()을 진입점으로 사용한다.
파트별 1회 실행이 원칙이며, 동일 파트명이 이미 존재하면 ValueError로 중단한다.

처리 순서:
  1. [Guard] parts 테이블에 part_name 존재 여부 확인
  2. parts 테이블에 신규 파트 INSERT
  3. 이미지별 OCR (Claude Vision) → 텍스트 추출
  4. 추출된 텍스트로 문제 생성 (Claude API) → JSON 파싱
  5. questions 테이블에 INSERT
  6. API 오류 발생 이미지는 skipped_images에 기록 후 계속 진행
"""
import base64
import json
import re
import sys

from pipeline.prompts import OCR_PROMPT, make_question_generation_prompt

_MEDIA_TYPE_MAP = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}


def run_pipeline(
    image_paths: list[str],
    part_name: str,
    supabase,
    anthropic_client,
    question_count: int = 10,
    order_num: int = 1,
) -> dict:
    """
    이미지 파일 목록과 파트명을 받아 문제를 생성하고 Supabase에 저장한다.

    Args:
        image_paths     : 처리할 이미지 파일 경로 목록 (JPEG/PNG)
        part_name       : 파트명 (예: "리스크관리")
        supabase        : Supabase 클라이언트
        anthropic_client: Anthropic 클라이언트
        question_count  : 유형별 생성 문제 수 (기본 10)
        order_num       : 파트 정렬 순번 (기본 1)

    Returns:
        {"inserted": int, "skipped_images": list[str]}

    Raises:
        ValueError: 해당 part_name이 이미 parts 테이블에 존재하는 경우
    """
    # Guard: 중복 실행 방지
    existing_parts = (
        supabase.table("parts").select("*").eq("name", part_name).execute()
    )
    if existing_parts.data:
        raise ValueError(
            f"파트 '{part_name}'이 이미 존재합니다. "
            "기존 데이터를 삭제 후 재시도하세요."
        )

    # 신규 파트 INSERT
    part_result = (
        supabase.table("parts")
        .insert({"name": part_name, "order_num": order_num})
        .execute()
    )
    part_id: str = part_result.data[0]["id"]

    inserted_count = 0
    skipped_images: list[str] = []

    for image_path in image_paths:
        try:
            # 1. OCR: 이미지 → 텍스트 추출
            extracted_text = _extract_text_from_image(
                image_path, anthropic_client
            )

            # 2. 문제 생성: 텍스트 → JSON
            questions_data = _generate_questions(
                extracted_text, anthropic_client, question_count
            )

            # 3. questions 레코드 빌드
            question_records = _build_question_records(questions_data, part_id)

            if question_records:
                supabase.table("questions").insert(question_records).execute()
                inserted_count += len(question_records)

        except Exception as e:
            print(f"[SKIP] {image_path}: {e}", file=sys.stderr)
            skipped_images.append(image_path)

    return {"inserted": inserted_count, "skipped_images": skipped_images}


def _extract_text_from_image(image_path: str, anthropic_client) -> str:
    """Claude Vision API로 이미지 텍스트를 추출한다."""
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = image_path.lower().rsplit(".", 1)[-1]
    media_type = _MEDIA_TYPE_MAP.get(ext, "image/jpeg")

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }
        ],
    )
    return response.content[0].text


def _generate_questions(
    text: str,
    anthropic_client,
    question_count: int,
) -> dict:
    """Claude API로 학습 자료 텍스트에서 문제를 생성하고 JSON으로 파싱한다."""
    prompt = make_question_generation_prompt(text, question_count)

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip())
    return json.loads(cleaned)


def _build_question_records(questions_data: dict, part_id: str) -> list[dict]:
    """
    API 응답 JSON을 Supabase questions 테이블 INSERT용 레코드 목록으로 변환한다.
    """
    records: list[dict] = []

    for q_type in ("ox", "fill", "mcq"):
        for q in questions_data.get(q_type, []):
            record = {
                "part_id": part_id,
                "type": q_type,
                "content": q["content"],
                "answer": q["answer"],
                "choices": q.get("choices"),
                "explanation": q.get("explanation"),
            }
            records.append(record)

    return records
