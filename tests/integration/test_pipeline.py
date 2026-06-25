"""
AC8: OCR 파이프라인 스크립트 실행 시 동일 파트명이 이미 존재하면 오류 출력 후 중단한다.
AC9: OCR 파이프라인 스크립트 실행 시 questions 테이블에 문제가 INSERT된다.

테스트 대상:
  - pipeline.ocr_and_generate.run_pipeline(
        image_paths: list[str],
        part_name: str,
        supabase,
        anthropic_client,
        question_count: int = 10,
    ) -> dict
    반환 형태: {"inserted": int, "skipped_images": list[str]}

Guard 조건 (AC8):
  parts 테이블에 해당 part_name이 이미 존재하면 SystemExit 또는 ValueError를 발생시킨다.
  → 중복 실행 방지

INSERT 조건 (AC9):
  parts에 part_name이 없으면 정상 실행: parts INSERT → questions INSERT
"""
import os
import pytest
from unittest.mock import MagicMock, patch, ANY


def _make_supabase_for_pipeline(part_exists: bool, existing_part=None, inserted_questions=None):
    """
    pipeline.run_pipeline이 사용하는 supabase 호출을 시뮬레이션한다.
    inserted_questions: list — 호출 중 INSERT된 문제들이 여기에 쌓인다.
    """
    if inserted_questions is None:
        inserted_questions = []

    def dispatch(table_name):
        t = MagicMock()

        if table_name == "parts":
            if part_exists:
                # Guard: 이미 존재하는 파트
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(
                    data=[existing_part or {"id": "existing-part-id", "name": "리스크관리"}]
                )
            else:
                # 파트 없음 → INSERT 허용
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
                new_part = {"id": "new-part-id", "name": "리스크관리", "order_num": 1}
                t.insert.return_value.execute.return_value = MagicMock(data=[new_part])

        elif table_name == "questions":
            def capture_questions_insert(data):
                rows = data if isinstance(data, list) else [data]
                inserted_questions.extend(rows)
                m = MagicMock()
                m.execute.return_value = MagicMock(data=rows)
                return m

            t.insert.side_effect = capture_questions_insert

        return t

    mock_supabase = MagicMock()
    mock_supabase.table.side_effect = dispatch
    return mock_supabase


def _make_anthropic_mock_with_questions():
    """
    Claude API가 이미지에서 문제를 생성하는 응답을 시뮬레이션한다.
    실제 API 호출 없이 문제 JSON을 반환하는 mock.
    """
    import json

    sample_questions = {
        "ox": [
            {"content": "리스크는 손실 가능성이다.", "answer": "O", "explanation": "기본 정의"},
        ] * 10,
        "fill": [
            {"content": "리스크의 반대는 ___이다.", "answer": "기회", "explanation": "설명"},
        ] * 10,
        "mcq": [
            {
                "content": "리스크 관리 방법이 아닌 것은?",
                "answer": "3",
                "choices": ["회피", "감소", "투기", "전가"],
                "explanation": "투기는 경감 기법이 아님",
            }
        ] * 10,
    }

    mock_client = MagicMock()
    # vision call (이미지 → 텍스트)
    vision_response = MagicMock()
    vision_response.content = [MagicMock(text="추출된 텍스트 내용")]
    # generate call (텍스트 → 문제 JSON)
    generate_response = MagicMock()
    generate_response.content = [MagicMock(text=json.dumps(sample_questions))]

    mock_client.messages.create.side_effect = [
        vision_response,    # 첫 번째 호출: OCR
        generate_response,  # 두 번째 호출: 문제 생성
    ]
    return mock_client


class TestPipelineGuard:
    """AC8: 동일 파트 재실행 시 오류 중단."""

    def test_raises_when_part_already_exists(self, tmp_path):
        """parts 테이블에 이미 해당 파트명이 있으면 예외가 발생한다."""
        from pipeline.ocr_and_generate import run_pipeline

        mock_supabase = _make_supabase_for_pipeline(part_exists=True)
        mock_anthropic = MagicMock()

        image_file = tmp_path / "test_image.jpg"
        image_file.write_bytes(b"fake image data")

        with pytest.raises((SystemExit, ValueError, RuntimeError)):
            run_pipeline(
                image_paths=[str(image_file)],
                part_name="리스크관리",
                supabase=mock_supabase,
                anthropic_client=mock_anthropic,
            )

    def test_guard_check_queries_parts_table(self, tmp_path):
        """Guard는 반드시 parts 테이블에서 part_name을 조회해야 한다."""
        from pipeline.ocr_and_generate import run_pipeline

        mock_supabase = _make_supabase_for_pipeline(part_exists=True)
        mock_anthropic = MagicMock()
        image_file = tmp_path / "img.jpg"
        image_file.write_bytes(b"fake")

        try:
            run_pipeline(
                image_paths=[str(image_file)],
                part_name="리스크관리",
                supabase=mock_supabase,
                anthropic_client=mock_anthropic,
            )
        except (SystemExit, ValueError, RuntimeError):
            pass

        # parts 테이블이 조회되었는지 확인
        assert mock_supabase.table.call_args_list, "supabase.table이 호출되지 않았다"
        called_tables = [c.args[0] for c in mock_supabase.table.call_args_list]
        assert "parts" in called_tables, f"parts 테이블이 조회되지 않았다. 조회된 테이블: {called_tables}"

    def test_does_not_call_anthropic_when_part_exists(self, tmp_path):
        """파트가 이미 존재하면 API 호출 없이 중단한다."""
        from pipeline.ocr_and_generate import run_pipeline

        mock_supabase = _make_supabase_for_pipeline(part_exists=True)
        mock_anthropic = MagicMock()
        image_file = tmp_path / "img.jpg"
        image_file.write_bytes(b"fake")

        try:
            run_pipeline(
                image_paths=[str(image_file)],
                part_name="리스크관리",
                supabase=mock_supabase,
                anthropic_client=mock_anthropic,
            )
        except (SystemExit, ValueError, RuntimeError):
            pass

        mock_anthropic.messages.create.assert_not_called()


class TestPipelineInsert:
    """AC9: questions 테이블에 문제가 INSERT된다."""

    def test_questions_inserted_to_supabase(self, tmp_path):
        """파이프라인 정상 실행 시 questions 테이블에 문제가 INSERT된다."""
        from pipeline.ocr_and_generate import run_pipeline

        inserted_questions = []
        mock_supabase = _make_supabase_for_pipeline(
            part_exists=False, inserted_questions=inserted_questions
        )
        mock_anthropic = _make_anthropic_mock_with_questions()

        image_file = tmp_path / "scan.jpg"
        image_file.write_bytes(b"fake image data")

        result = run_pipeline(
            image_paths=[str(image_file)],
            part_name="리스크관리",
            supabase=mock_supabase,
            anthropic_client=mock_anthropic,
        )

        assert inserted_questions, "questions 테이블에 INSERT가 발생하지 않았다"

    def test_inserted_questions_have_required_fields(self, tmp_path):
        """INSERT되는 문제는 type, content, answer, part_id 필드를 포함해야 한다."""
        from pipeline.ocr_and_generate import run_pipeline

        inserted_questions = []
        mock_supabase = _make_supabase_for_pipeline(
            part_exists=False, inserted_questions=inserted_questions
        )
        mock_anthropic = _make_anthropic_mock_with_questions()

        image_file = tmp_path / "scan.jpg"
        image_file.write_bytes(b"fake image data")

        run_pipeline(
            image_paths=[str(image_file)],
            part_name="리스크관리",
            supabase=mock_supabase,
            anthropic_client=mock_anthropic,
        )

        for q in inserted_questions:
            assert "type" in q, f"type 필드 누락: {q}"
            assert "content" in q, f"content 필드 누락: {q}"
            assert "answer" in q, f"answer 필드 누락: {q}"
            assert "part_id" in q, f"part_id 필드 누락: {q}"
            assert q["type"] in ("ox", "fill", "mcq"), f"type 값 오류: {q['type']}"

    def test_result_contains_inserted_count(self, tmp_path):
        """반환값에 생성된 문제 수가 포함된다."""
        from pipeline.ocr_and_generate import run_pipeline

        inserted_questions = []
        mock_supabase = _make_supabase_for_pipeline(
            part_exists=False, inserted_questions=inserted_questions
        )
        mock_anthropic = _make_anthropic_mock_with_questions()

        image_file = tmp_path / "scan.jpg"
        image_file.write_bytes(b"fake image data")

        result = run_pipeline(
            image_paths=[str(image_file)],
            part_name="리스크관리",
            supabase=mock_supabase,
            anthropic_client=mock_anthropic,
        )

        assert "inserted" in result, f"반환값에 'inserted' 키가 없다: {result}"
        assert result["inserted"] > 0

    def test_result_contains_skipped_images_list(self, tmp_path):
        """반환값에 실패한 이미지 목록이 포함된다."""
        from pipeline.ocr_and_generate import run_pipeline

        inserted_questions = []
        mock_supabase = _make_supabase_for_pipeline(
            part_exists=False, inserted_questions=inserted_questions
        )
        mock_anthropic = _make_anthropic_mock_with_questions()

        image_file = tmp_path / "scan.jpg"
        image_file.write_bytes(b"fake image data")

        result = run_pipeline(
            image_paths=[str(image_file)],
            part_name="리스크관리",
            supabase=mock_supabase,
            anthropic_client=mock_anthropic,
        )

        assert "skipped_images" in result, f"반환값에 'skipped_images' 키가 없다: {result}"
        assert isinstance(result["skipped_images"], list)

    def test_api_error_on_image_is_skipped_not_aborted(self, tmp_path):
        """이미지 처리 중 API 오류 발생 시 해당 이미지는 건너뛰고 계속 진행한다."""
        from pipeline.ocr_and_generate import run_pipeline
        import json

        inserted_questions = []
        mock_supabase = _make_supabase_for_pipeline(
            part_exists=False, inserted_questions=inserted_questions
        )

        # 첫 번째 이미지: API 오류 / 두 번째 이미지: 성공
        sample_questions = {
            "ox": [{"content": "Q", "answer": "O", "explanation": "E"}],
            "fill": [],
            "mcq": [],
        }
        mock_anthropic = MagicMock()
        mock_anthropic.messages.create.side_effect = [
            Exception("API 오류"),                                          # OCR 실패
            MagicMock(content=[MagicMock(text="텍스트")]),                 # 두 번째 이미지 OCR 성공
            MagicMock(content=[MagicMock(text=json.dumps(sample_questions))]),  # 문제 생성 성공
        ]

        img1 = tmp_path / "fail.jpg"
        img2 = tmp_path / "ok.jpg"
        img1.write_bytes(b"bad image")
        img2.write_bytes(b"good image")

        result = run_pipeline(
            image_paths=[str(img1), str(img2)],
            part_name="리스크관리",
            supabase=mock_supabase,
            anthropic_client=mock_anthropic,
        )

        assert str(img1) in result["skipped_images"], "실패한 이미지가 skipped_images에 포함되어야 한다"
        assert result["inserted"] > 0, "성공한 이미지의 문제는 INSERT되어야 한다"
