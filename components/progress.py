"""
사용자 학습 진도 관련 DB 조작 모듈.

upsert_progress   : 문제 풀기 결과를 user_progress 테이블에 UPSERT
toggle_bookmark   : 즐겨찾기 on/off 토글
get_wrong_notes   : 오답 노트 목록 조회 (wrong_count > 0, 내림차순)
get_bookmarks     : 즐겨찾기 목록 조회
get_progress_dashboard : 파트별 진도 현황 계산
"""
from datetime import datetime, timezone


def upsert_progress(
    user_id: str,
    question_id: str,
    is_correct: bool,
    supabase,
) -> dict:
    """
    문제 풀기 결과를 user_progress에 반영한다.

    SELECT → 없으면 INSERT, 있으면 UPDATE 패턴.
    attempt_count 누적, 정/오답 카운트 누적, last_attempted_at 및 last_correct 갱신.
    """
    result = (
        supabase.table("user_progress")
        .select("*")
        .eq("user_id", user_id)
        .eq("question_id", question_id)
        .execute()
    )

    now = datetime.now(timezone.utc).isoformat()

    if not result.data:
        new_record = {
            "user_id": user_id,
            "question_id": question_id,
            "attempt_count": 1,
            "correct_count": 1 if is_correct else 0,
            "wrong_count": 0 if is_correct else 1,
            "is_bookmarked": False,
            "last_attempted_at": now,
            "last_correct": is_correct,
        }
    else:
        existing = result.data[0]
        new_record = {
            **existing,
            "attempt_count": existing["attempt_count"] + 1,
            "correct_count": existing["correct_count"] + (1 if is_correct else 0),
            "wrong_count": existing["wrong_count"] + (0 if is_correct else 1),
            "last_attempted_at": now,
            "last_correct": is_correct,
        }

    upsert_result = (
        supabase.table("user_progress")
        .upsert(new_record, on_conflict="user_id,question_id")
        .execute()
    )
    return upsert_result.data[0]


def toggle_bookmark(user_id: str, question_id: str, supabase) -> bool:
    """
    즐겨찾기 상태를 반전한다.

    레코드가 없으면 is_bookmarked=True로 신규 생성.
    Returns:
        새로운 is_bookmarked 값 (bool)
    """
    result = (
        supabase.table("user_progress")
        .select("*")
        .eq("user_id", user_id)
        .eq("question_id", question_id)
        .execute()
    )

    if not result.data:
        supabase.table("user_progress").upsert(
            {
                "user_id": user_id,
                "question_id": question_id,
                "is_bookmarked": True,
            }
        ).execute()
        return True

    existing = result.data[0]
    new_value = not existing["is_bookmarked"]

    supabase.table("user_progress").update(
        {"is_bookmarked": new_value}
    ).eq("user_id", user_id).eq("question_id", question_id).execute()

    return new_value


def get_wrong_notes(
    user_id: str,
    supabase,
    part_id: str | None = None,
) -> list[dict]:
    """
    오답 노트 목록을 반환한다.

    - wrong_count > 0인 user_progress 레코드만 포함
    - wrong_count 내림차순 정렬
    - part_id 지정 시 DB 레벨 필터링 (questions 조인 후 part_id 조건 적용)
    """
    if part_id is not None:
        result = (
            supabase.table("user_progress")
            .select("*, questions!inner(part_id)")
            .eq("user_id", user_id)
            .gt("wrong_count", 0)
            .eq("questions.part_id", part_id)
            .execute()
        )
    else:
        result = (
            supabase.table("user_progress")
            .select("*")
            .eq("user_id", user_id)
            .gt("wrong_count", 0)
            .execute()
        )

    rows = result.data or []
    rows = [{k: v for k, v in r.items() if k != "questions"} for r in rows]
    rows.sort(key=lambda r: r["wrong_count"], reverse=True)
    return rows


def get_bookmarks(user_id: str, supabase) -> list[dict]:
    """is_bookmarked=True인 user_progress 레코드 목록을 반환한다."""
    result = (
        supabase.table("user_progress")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_bookmarked", True)
        .execute()
    )
    return result.data or []


def get_progress_dashboard(user_id: str, supabase) -> list[dict]:
    """
    파트별 진도 현황을 계산하여 반환한다.

    반환 형태:
        [
            {
                "part_id": str,
                "part_name": str,
                "total_questions": int,
                "attempted_count": int,
                "accuracy": float,   # correct_count / attempt_count * 100
            },
            ...
        ]

    attempt_count=0인 파트(아직 풀지 않음)도 포함하며 accuracy=0.0으로 반환.
    """
    parts = (
        supabase.table("parts").select("*").order("order_num").execute().data or []
    )
    questions = (
        supabase.table("questions").select("*").execute().data or []
    )
    progress_rows = (
        supabase.table("user_progress")
        .select("*")
        .eq("user_id", user_id)
        .execute()
        .data or []
    )

    # question_id → progress row 인덱스
    progress_by_question: dict[str, dict] = {
        row["question_id"]: row for row in progress_rows
    }

    # part_id → question 목록 인덱스
    questions_by_part: dict[str, list] = {}
    for q in questions:
        pid = q["part_id"]
        questions_by_part.setdefault(pid, []).append(q)

    dashboard = []
    for part in parts:
        pid = part["id"]
        part_questions = questions_by_part.get(pid, [])
        total_questions = len(part_questions)

        part_progress = [
            progress_by_question[q["id"]]
            for q in part_questions
            if q["id"] in progress_by_question
        ]

        attempted_count = len(part_progress)
        total_attempt = sum(p["attempt_count"] for p in part_progress)
        total_correct = sum(p["correct_count"] for p in part_progress)

        accuracy = (total_correct / total_attempt * 100) if total_attempt > 0 else 0.0

        dashboard.append(
            {
                "part_id": pid,
                "part_name": part["name"],
                "total_questions": total_questions,
                "attempted_count": attempted_count,
                "accuracy": accuracy,
            }
        )

    return dashboard
