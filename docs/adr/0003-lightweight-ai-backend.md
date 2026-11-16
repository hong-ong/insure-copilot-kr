# ADR-0003: 임베딩·파서를 가볍게 — Gemini 임베딩 + 자체 파서, 무료 배포 조합

- 날짜: 2026-10-19
- 상태: 채택 (5주차 E2 실험 결과로 재검토)

## 맥락
- 커리큘럼은 bge-m3(로컬 임베딩)와 Docling(PDF 파서)을 쓴다. 둘 다 PyTorch를 필요로 해 설치 용량이 수 GB이고,
  이 PC는 Smart App Control이 서명 없는 DLL을 막아 PyTorch 계열이 실패할 위험이 있다.
- 공개 데모는 무료로 상시 띄워야 한다. 무료 서버는 메모리가 작다.
- 업로드 파일은 자동으로 파싱·품질 판정(한글 인식률 90%)을 해야 한다.

## 선택지
| 안 | 장점 | 단점 |
| --- | --- | --- |
| A. bge-m3 + Docling (커리큘럼) | 로컬 실행, API 의존 없음, 표 추출 우수 | 수 GB 의존성, 무료 서버에서 느림, 이 PC에서 설치 위험 |
| B. Gemini 임베딩 API + PyMuPDF·HWP·DOCX 직접 파싱 + Gemini 비전 OCR | 의존성 가벼움, 무료 티어로 비용 0, 한국어 OCR 품질 좋음 | API 호출 한도, 무료 티어 입력은 모델 개선에 쓰일 수 있음(→ 가상 데이터만 사용) |

배포 조합 비교 (무료 기준)

| 백엔드 후보 | 메모리 | 비고 |
| --- | --- | --- |
| Hugging Face Spaces (Docker) | 16GB급 | 미사용 시 잠듦, Docker로 배포 |
| Render 무료 | 512MB | 15분 미사용 시 잠듦, 메모리 부족 위험 |
| Fly.io | — | 무료 플랜 없음 |

## 결정
B + Hugging Face Spaces. 임베딩은 LiteLLM을 거쳐 `gemini/gemini-embedding-001`(768차원)로 호출한다.
임베딩 함수를 한 곳(`llm/gateway.py`)에 모아 두어, 5주차 E2 실험에서 bge-m3·KURE와 바꿔 끼울 수 있게 한다.

## 결과와 트레이드오프
- 얻은 것: 가벼운 컨테이너, 무료 상시 데모, 이 PC에서 설치 위험 없음
- 포기한 것: 로컬 임베딩(오프라인·망분리 환경 대응) — 면접 질문 "망분리 환경이면?"의 답으로 A안을 설명
- 재검토 조건: E2에서 bge-m3/KURE가 Recall@5를 5%p 이상 높이면 교체(차원이 바뀌므로 재색인 필요)

## 개정 2026-10-21

**바뀐 것:** 배포 대상을 Hugging Face Spaces → **Vercel Python 함수**(프로젝트 `gaon-ax-api`, 리전 bom1)로 바꿨다.
임베딩·파서 결정(B안: Gemini 임베딩 + 자체 파서)은 그대로다.

**경위**
- 2026-10-19 (`ee0ec83`): Hugging Face가 무료 CPU Docker Space를 PRO 전용으로 바꿔(402 응답) Render 무료(512MB)로 변경했다.
  메모리 실측 결과 API 약 230MB + Kiwi 모델 약 500MB라서 `KIWI_ENABLED=false` 스위치를 추가했다.
- 2026-10-21 (`9a9ceac`): Render는 별도 가입이 필요해 Vercel Python 함수로 배포했다. Kiwi는 빼고, 마트는 첫 호출 때 `/tmp`에 만든다.

**바뀐 트레이드오프** (`docs/setup.md` 5장)
- 얻은 것: 잠들지 않음, 메모리 2GB
- 포기한 것: 요청 본문 4.5MB 한도 → 구성안의 업로드 10MB 한도보다 큰 파일은 실패. Kiwi(100MB+)는 함수 용량 한도로 제외
- HF 배포 스크립트(`scripts/deploy_hf.py`)는 HF PRO를 쓸 경우를 위해 보관
