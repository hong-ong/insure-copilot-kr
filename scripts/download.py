# 2주차 — 원문 다운로드 스크립트 (나중에 작성)
#
# 원문은 저장소에 올리지 않으므로(data/raw/ 는 gitignore), 이 스크립트로 누구나 같은 파일을 다시 받을 수 있게 한다.
# 출처·발령일·받은 날짜는 data/SOURCES.md 에 기록한다.
#
# 지금까지 수동으로 받은 방법 (2026-10-21)
#   - 국가법령정보 Open API(LAW_API_OC)로 보험업감독업무시행세칙(행정규칙) XML 조회
#     https://www.law.go.kr/DRF/lawService.do?OC=<OC>&target=admrul&ID=2200000108939&type=XML
#   - XML의 별표15(표준약관) 항목에서 <별표서식PDF파일링크> → https://www.law.go.kr/LSW/flDownload.do?flSeq=168885301
#     (<별표서식파일링크> flSeq=168884315 는 같은 내용의 HWP)
#   - 492쪽 전체 중 실손의료보험(기본형·특약1·특약2) = PDF 204-313쪽 → data/raw/silson_standard.pdf
#     (목차 쪽번호는 실제와 1쪽 어긋나므로 "□기본형실손의료보험" 제목 줄로 경계를 찾았다)
