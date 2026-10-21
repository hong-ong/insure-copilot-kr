# CLAUDE.md — insure-copilot-kr

이 저장소는 **보험 약관·규정 AI 어시스턴트**를 8주 동안 만드는 개인 포트폴리오 프로젝트다.
목적은 "AI 기획자(AI PM)로서 AI 서비스를 기획하고, 품질을 정의하고, 수치로 검증할 수 있다"를 보여주는 것이다.
전체 계획은 `docs/curriculum.md`에 있다. 작업 전에 해당 주차 섹션을 먼저 읽는다.

> **2026-10-19부터 10 → 1(역방향) 방식.** 완성형 서비스 "가온생명 AX 어시스턴트"를 먼저 만들고,
> 기능별 "갭 체크카드"로 부족한 공부를 메운다. 구성안: `docs/planning/00-portfolio-plan.md` (기능·화면의 기준 문서).

## 사용자에 대해

- 저장소 주인은 기획자다. 개발은 배우는 중이다. 코드 설명과 용어 설명을 아끼지 않는다.
- 처음 나오는 용어(예: top-k, MRR, RRF)는 그 자리에서 한 줄로 설명한다.
- 사용자가 질문 목록에 답하라고 하면, 각 답변 위에 질문을 인용한다.
- 응답과 문서, 커밋 메시지 본문은 한국어로 쓴다. 코드 식별자와 주석은 영어도 괜찮지만 docstring 첫 줄은 한국어로 쓴다.

## 제품 한 줄 요약

가상의 보험사 AX팀이 설계사·콜센터 상담원·본사 교육/준법 담당을 위해 만드는 사내 어시스턴트.
라우터가 질문을 세 갈래로 보낸다.

1. **약관·규정 RAG** — 표준약관·보험업법·분쟁조정사례를 근거로 답하고 출처(문서명·조항·약관 버전)를 표시한다.
2. **GenBI** — 설계사·계약 데이터 마트에서 미리 정의한 지표로 계산한다. 역할별 행 단위 권한을 적용한다.
3. **거절** — "이 고객 보험금 받을 수 있나요?" 같은 판단 요구는 근거 조문만 안내하고 판단은 거절한다.

어느 경로든 답변 검증(근거 없음·판단성 답변이면 거절)을 통과해야 사용자에게 나간다.

## 절대 규칙 (학습 규칙 — 반드시 지킨다)

1. **"직접 작성" 부분은 대신 쓰지 않는다.** 각 주차에 사용자가 AI 없이 직접 쓰기로 한 부분이 있다.
   아래 표의 항목을 요청받으면 완성 코드를 주지 말고 힌트·설계 질문·리뷰로만 돕는다.
   사용자가 "직접 작성 끝났어, 리뷰해줘"라고 하면 그때 리뷰한다.
   해당 파일에는 `# [직접 작성]` 표시가 있다.

   | 주차 | 직접 작성 항목 |
   | --- | --- |
   | 1 | LLM 호출 스크립트 (모델·프롬프트·응답 시간 출력) — `scripts/w01_llm_call.py` |
   | 2 | 관·조·항 번호 정규식과 청크 스키마 |
   | 3 | 골든셋 50문항 (초안은 AI 가능, 정답·근거는 사용자가 약관에서 직접 확인) |
   | 4 | Recall@5·MRR 계산 함수 |
   | 5 | 보험 동의어 사전 30개 |
   | 6 | 지표 5개의 정답 SQL |
   | 7 | 의도 분류 프롬프트와 분기 조건 |

   **10 → 1 예외 (2026-10-19 합의):** 서비스 동작에 꼭 필요한 직접 작성 항목(2주차 조항 정규식·청크 스키마,
   6주차 지표 SQL, 7주차 의도 분류 프롬프트)은 AI가 **임시본**을 만든다. 임시본에는
   `[임시-AI작성 → 직접 작성으로 교체]` 표시를 달고, 사용자가 해당 주차 공부 때 직접 다시 써서 교체한다.
   교체 후 표시를 `[직접 작성]`으로 바꾼다. 평가용 항목(골든셋·Recall@5/MRR·동의어 사전)은 임시본 없이 빈 틀로 둔다.

2. **함수마다 "무엇을 왜 하는가" 한 문장.** AI가 쓴 코드도 커밋 전에 사용자가 직접 docstring을 다는 게 원칙이다.
   새 함수를 만들 때는 docstring 자리에 `TODO(재홍): 무엇을 왜 하는가 한 문장`을 남겨 사용자가 채우게 한다.
   10 → 1 방식에서는 AI가 만든 Python 함수가 TODO docstring을 단 채로 커밋되고, 채우는 일이 갭 체크의 일부다.
   (TypeScript 화면 코드는 컴포넌트 단위 한 줄 주석만 둔다.)
3. **실험은 학습 로그에 남긴다.** 실험을 돌리면 `docs/learning-log.md`에 날짜 · 가설 · 결과 · 배운 점 형식으로 항목 초안을 추가하고, "배운 점"은 사용자가 채우도록 비워 둔다.
4. **한 번에 변수 하나.** 5주차 실험은 변수 하나만 바꾼다. 여러 개를 섞자고 하면 먼저 경고한다.
5. **실패한 실험도 지우지 않는다.** 결과가 나빠도 기록이 포트폴리오 재료다.

## 데이터·보안 규칙

- 원문 파일(PDF·HWP·법령 원문)은 커밋하지 않는다. `data/raw/`와 `data/processed/`는 gitignore 대상이다. 다운로드 스크립트와 `data/SOURCES.md` 출처 목록만 남긴다.
- API 키는 `.env`에만 둔다. 코드·로그·커밋에 키를 쓰지 않는다.
- 개인정보(주민번호·연락처·계좌번호)와 **건강정보(병력·진단명 = 민감정보)** 는 입력·로그 양쪽에서 마스킹한다. 테스트 데이터도 가상 데이터만 쓴다.
- 이전 직장 제안서의 원본·도식·문구·기대효과 수치는 저장소에 넣지 않는다. 직접 측정한 수치만 쓴다.

## 기술 스택

- **화면:** Next.js (App Router, TypeScript, Tailwind) — `web/`. Node는 `C:\develop\_tools\node` (PATH 미등록, 세션 PATH로 사용)
- **인증·DB·파일:** Supabase (Auth: 이메일·Google·Kakao·익명=데모 계정, Postgres + pgvector, Storage). 권한은 RLS로 강제
- **AI 백엔드:** Python 3.12 + uv + FastAPI — `src/insure_copilot/`. uv는 `C:\develop\_tools\uv\uv.exe`
- LLM·임베딩 호출은 반드시 **LiteLLM**을 거친다 (모델 교체·비용 로그·fallback을 한 곳에서). 공급자 SDK를 직접 부르지 않는다.
  - 주 모델: Gemini 무료 티어 (`gemini/gemini-flash-latest`, fallback `gemini/gemini-flash-lite-latest`), 임베딩 `gemini/gemini-embedding-001`(768차원)
- 파서: PyMuPDF(PDF) · HWP5(olefile) · HWPX(XML) · python-docx, 글자가 깨지면 Gemini 비전 OCR로 재시도
- 정보계: DuckDB + Faker 가상 데이터 / 관측: Langfuse(키가 있을 때만)
- 배포: Vercel(web: gaon-ax) + Vercel Python 함수(api: gaon-ax-api) + Supabase — `docs/setup.md` 5장
- 커리큘럼(Streamlit·Chroma·bge-m3·Docling)과 다른 이유는 `docs/adr/0001~0003`. 커리큘럼 실험(E2 임베딩 비교 등)은 이 구조 위에서 그대로 한다.
- 린트·포맷: ruff. 테스트: pytest.

## 저장소 구조

```
web/                  # Next.js 화면 (ChatGPT형 레이아웃)
supabase/migrations/  # DB 스키마·RLS
src/insure_copilot/   # AI 백엔드 (api/, ingest/, retrieval/, agent/, genbi/, meetings/, llm/, store/)
data/samples/         # 가온생명 가상 문서 (직접 만든 가상 데이터라 커밋 가능)
scripts/              # 주차별 실행 스크립트 (w01_*, w02_* ...)
eval/golden/          # 골든셋 CSV (3주차~)
eval/results/         # 평가 실행 결과 (gitignore, 요약표만 docs로 옮김)
data/                 # raw/processed는 커밋 금지, SOURCES.md만 커밋
docs/curriculum.md    # 8주 계획 원본
docs/planning/        # 기획 산출물 (문제 정의서, PRD, 지표 정의서 ...)
docs/notes/           # 주차별 학습 노트
docs/adr/             # 의사결정 기록
docs/learning-log.md  # 실험·학습 로그
tests/
```

## 자주 쓰는 명령

```bash
uv sync                      # 환경 구성
uv run pytest                # 테스트
uv run ruff check . --fix    # 린트
uv run ruff format .         # 포맷
uv run python scripts/w01_llm_call.py   # 1주차 LLM 호출 (사용자가 직접 작성)
uv run uvicorn insure_copilot.api.main:app --reload --port 8000   # AI 백엔드
cd web && npm run dev                                              # 화면 (localhost:3000)
```

## 작업 방식

- 주차를 시작할 때는 `/week-start N` 커맨드로 그 주 체크리스트를 확인하고 계획부터 세운다.
- 커밋은 작게, 메시지 제목은 `[wNN] 무엇을 했는지` 형식 (예: `[w01] 베이스라인 0 결과 기록`). 10 → 1 서비스 제작 커밋은 `[build] ...`.
- 관문 기준을 못 채우면 다음 주차로 넘어가지 말자고 제안한다.
- 비용: 4주차부터 평가를 반복 실행하므로 LiteLLM 비용 로그를 확인하고, 큰 배치를 돌리기 전에 예상 비용을 먼저 말한다.
