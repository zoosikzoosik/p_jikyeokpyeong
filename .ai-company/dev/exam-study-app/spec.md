# spec: 직무역량평가 학습 앱

## 개요

회사 직무역량평가(100점 만점, 70점 통과) 준비를 위한 개인용 웹 학습 앱.
총 9개 파트의 스캔 인쇄물을 OCR로 텍스트화하고, AI가 문제를 자동 생성하여 Streamlit 웹앱에서 풀 수 있다.
Streamlit Cloud에 배포하여 PC/모바일 어디서든 URL로 접속 가능.

## 기술 스택

| 항목 | 선택 |
|------|------|
| 프론트엔드 | Streamlit |
| DB | Supabase (PostgreSQL) |
| LLM | Claude API (claude-sonnet-4-6) |
| 배포 | Streamlit Cloud |
| 인증 | 커스텀 닉네임 + 비밀번호 (Supabase users 테이블) |
| 언어 | Python 3.11+ |

## DB 스키마 (Supabase)

### parts
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| name | text NOT NULL UNIQUE | 파트명 (리스크, 금융, 카드상품 등) |
| order_num | int NOT NULL | 정렬 순서 |
| created_at | timestamptz | |

### questions
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| part_id | uuid FK → parts.id | |
| type | text NOT NULL CHECK (type IN ('ox', 'fill', 'mcq')) | 'ox' / 'fill' / 'mcq' |
| content | text NOT NULL | 문제 본문 |
| answer | text NOT NULL | 정답 (OX: 'O'/'X', 빈칸: 정답 문자열, 객관식: '1'~'4') |
| choices | jsonb | 객관식 보기 4개 ["보기1","보기2","보기3","보기4"] |
| explanation | text | 해설 (선택) |
| created_at | timestamptz | |

### users
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| nickname | text NOT NULL UNIQUE | 닉네임 (자유 입력, 길이/복잡도 제한 없음) |
| password_hash | text NOT NULL | bcrypt 해시 |
| created_at | timestamptz | |

### user_progress
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | uuid PK | |
| user_id | uuid FK → users.id | |
| question_id | uuid FK → questions.id | |
| attempt_count | int DEFAULT 0 | 총 시도 횟수 |
| wrong_count | int DEFAULT 0 | 틀린 횟수 |
| correct_count | int DEFAULT 0 | 맞은 횟수 |
| is_bookmarked | bool DEFAULT false | 즐겨찾기 여부 |
| last_attempted_at | timestamptz | 마지막 시도 시각 |
| last_correct | bool | 마지막 시도 정답 여부 |

UNIQUE (user_id, question_id)

## 기능 명세

### 1. 인증
- 앱 진입 시 닉네임 + 비밀번호 입력 화면
- 닉네임 없으면 회원가입 (닉네임 + 비밀번호 자유 입력, 제한 없음)
- 로그인 성공 시 `st.session_state`에 user_id 저장, 세션 유지
- 비밀번호는 bcrypt 해시로 저장/검증
- 비밀번호 분실 시 관리자가 Supabase 대시보드에서 직접 초기화 (공부 데이터 유지)

### 2. 메인 화면 (파트 선택)
- 9개 파트 카드 표시
- 각 카드에 진도 요약: "30/42 풀음 · 정답률 73%"
- 파트 클릭 → 문제 풀기 화면으로 이동
- 사이드바에 즐겨찾기 / 오답 노트 / 전체 진도 메뉴

### 3. 문제 풀기 화면

#### 공통
- 파트 내 문제를 랜덤 순서로 출제
- 문제 번호 / 전체 문제 수 표시
- 즐겨찾기 토글 버튼 (★)
- 정답 제출 후 즉시 O/X 피드백 + 해설 표시

#### OX 문제
- O / X 버튼 두 개

#### 빈칸 채우기
- 텍스트 입력창
- 완전 일치(trim + casefold)만 정답으로 인정, 부분 정답 없음

#### 4지선다 객관식
- 보기 4개 라디오 버튼

### 4. 오답 노트
- wrong_count > 0인 문제 목록
- 파트 필터 가능
- "틀린 횟수" 내림차순 정렬
- 오답 문제만 모아서 풀기 모드 진입 가능

### 5. 즐겨찾기
- is_bookmarked = true인 문제 목록
- 파트 필터 가능
- 즐겨찾기 문제만 모아서 풀기 모드 진입 가능

### 6. 전체 진도 현황
- 파트별 테이블: 전체 문제 수 / 풀어본 문제 수 / 정답률
- 전체 합계 행 포함
- 정답률 계산식: `correct_count / attempt_count × 100` (누적 기준). `last_correct`는 오답 노트 필터와 마지막 시도 표시에만 사용

## OCR 파이프라인 (별도 스크립트)

`pipeline/ocr_and_generate.py` — 스캔 완료 후 파트별 1회 실행.

```
입력: 이미지 파일 경로 목록 (JPEG/PNG) + 파트명
      PDF는 직접 지원 안 함 — 미리 이미지로 변환 필요

처리:
  0. [Guard] 해당 파트명이 parts 테이블에 이미 존재하면 오류 출력 후 중단
     → 중복 실행 방지. 재실행이 필요하면 기존 파트 데이터를 수동 삭제 후 재시도
  1. Claude Vision API로 이미지 → 텍스트 추출
  2. Claude API로 텍스트 → 문제 자동 생성
     - OX 문제 10개 (기본값, --count 인자로 변경 가능)
     - 빈칸 문제 10개
     - 4지선다 문제 10개
  3. 이미지 처리 중 API 오류 발생 시 해당 이미지 건너뛰고 계속 진행
  4. Supabase questions 테이블에 INSERT
출력: 생성된 문제 수 요약 + 실패한 이미지 목록
```

문제 생성 프롬프트는 `pipeline/prompts.py`에 분리.

## 프로젝트 구조

```
p_직역평/
├── app.py                    # Streamlit 앱 진입점
├── pages/
│   ├── 1_quiz.py             # 문제 풀기
│   ├── 2_wrong_notes.py      # 오답 노트
│   ├── 3_bookmarks.py        # 즐겨찾기
│   └── 4_progress.py         # 진도 현황
├── components/
│   ├── auth.py               # 인증 (닉네임+비밀번호, bcrypt)
│   ├── question_card.py      # 문제 컴포넌트 (OX/빈칸/객관식)
│   └── supabase_client.py    # DB 연결
├── pipeline/
│   ├── ocr_and_generate.py   # OCR + 문제 생성 스크립트
│   └── prompts.py            # LLM 프롬프트
├── .streamlit/
│   └── secrets.toml          # 비밀번호, Supabase URL/KEY, Claude API KEY
├── requirements.txt
└── .ai-company/dev/exam-study-app/
```

## 수용 기준

1. 비밀번호 없이는 앱에 접근할 수 없다
2. 파트 선택 후 OX / 빈칸 / 4지선다 문제를 풀 수 있다
3. 정답 제출 시 즉시 피드백과 해설이 표시된다
4. 문제 제출 시 해당 question_id로 user_progress를 UPSERT한다 — 없으면 INSERT, 있으면 attempt_count +1, 정답이면 correct_count +1 / 오답이면 wrong_count +1, last_attempted_at과 last_correct를 갱신한다. (검증: 동일 문제를 3회 풀어 2회 정답 처리하면 attempt_count=3, correct_count=2, wrong_count=1)
5. 즐겨찾기 토글이 DB에 반영되고 즐겨찾기 목록에서 확인된다
6. 오답 노트에서 wrong_count 내림차순으로 문제 목록이 표시된다
7. 진도 현황에서 파트별 풀어본 문제 수와 정답률이 표시된다
8. OCR 파이프라인 스크립트 실행 시 questions 테이블에 문제가 INSERT된다
9. Streamlit Cloud 배포 후 모바일 브라우저에서 정상 접속된다
