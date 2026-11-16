# 데이터 출처

원문 파일은 저장소에 올리지 않는다. 받은 파일은 `data/raw/`에 두고(gitignore), 여기에는 출처와 받은 날짜만 적는다.
2주차에 다운로드 스크립트(`scripts/w02_download.py` 예정)로 재현할 수 있게 만든다.

| 구분 | 문서 | 출처 | 형식 | 버전·시행일 | 받은 날짜 |
| --- | --- | --- | --- | --- | --- |
| 약관 | 실손의료보험 표준약관 (기본형·특약1 중증비급여·특약2 비중증비급여) → `silson_standard.pdf` | 보험업감독업무시행세칙 [별표15] 표준약관 PDF, 국가법령정보 Open API (`flSeq=168885301`, HWP 판 `168884315`). 492쪽 중 p.204-313 추출. 금감원 게시판 판은 2021-06 등록본이라 쓰지 않음 | PDF | 2026-08-28 발령 | 2026-10-21 |
| 약관 | 교보생명 전체 상품 · 전체 판매기간별 약관 (상품 1,128개 · 판매기간 8,244개 · 고유 PDF 7,997개 중 7,979개 수신, 57.8GB) → `E:\insure-copilot-data\kyobo\terms\` (용량 때문에 저장소 밖), 상품·기간·파일명 목록은 같은 폴더 `manifest.jsonl` | [교보생명 공시실 전체상품조회](https://www.kyobo.com/dgt/web/product-official/all-product/search) — `scripts/w02_download_kyobo.py download --out E:\insure-copilot-data\kyobo`. 못 받은 18개: 서버 404 10개, PDF가 아닌(암호화된 것으로 보이는) 응답 8개 — `download_log.jsonl` 참고. 판매기간 144개는 사이트에 약관 파일 자체가 없음 | PDF | 1980년대~2026-11 판매분 | 2026-11-11 |
| 약관 (실습 범위) | 교보실손의료비보험(갱신형)Ⅲ — 판 3개. 원본 `E:\insure-copilot-data\kyobo\terms\` (raw, 이동·수정 금지), 가공 결과 `E:\insure-copilot-data\kyobo\processed\`. **원본은 저장소에 넣지 않는다.** 파일 목록·sha256은 `data/manifest.csv` | 교보생명 공시(공개 약관) — 위 전체 수집분에서 선택 | PDF | 2016-01-01 · 2023-01-01 · 2026-01-01 | 2026-11-11 |
| 약관 (실습 범위) | 교보암보험[D2408](무배당,갱신형) — 판 3개. 원본 `E:\insure-copilot-data\kyobo\terms\` (raw, 이동·수정 금지), 가공 결과 `E:\insure-copilot-data\kyobo\processed\`. **원본은 저장소에 넣지 않는다.** 파일 목록·sha256은 `data/manifest.csv` | 교보생명 공시(공개 약관) — 위 전체 수집분에서 선택 | PDF | 2024-08-07 · 2025-04-01 · 2025-09-01 | 2026-11-11 |
| 약관 (실습 범위) | 교보하나로케어종신보험Ⅱ(보증비용부과형) — 판 3개. 원본 `E:\insure-copilot-data\kyobo\terms\` (raw, 이동·수정 금지), 가공 결과 `E:\insure-copilot-data\kyobo\processed\`. **원본은 저장소에 넣지 않는다.** 파일 목록·sha256은 `data/manifest.csv` | 교보생명 공시(공개 약관) — 위 전체 수집분에서 선택 | PDF | 2017-01-01 · 2023-01-01 · 2024-01-01 | 2026-11-11 |
| 약관 | 질병·상해보험 표준약관 | 보험업감독업무시행세칙 별표15 | | | |
| 약관 | 생명보험 표준약관 | 보험업감독업무시행세칙 별표15 | | | |
| 법규 | 보험업법·시행령 | [국가법령정보 Open API](https://open.law.go.kr/LSO/openApi/guideList.do) | | | |
| 법규 | 보험업감독규정 | 국가법령정보 Open API | | | |
| 법규 | 금융소비자보호법 (설명의무) | 국가법령정보 Open API | | | |
| 사례 | 금감원 보험 분쟁조정사례 | 금감원 | | | |
| 사내(가상) | 설계사 영업 가이드 등 3–5개 | 직접 작성 (가상) | md | | |
