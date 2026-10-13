# 평가

- `golden/` — 골든셋 CSV (3주차 v1 50문항 → 7주차 통합 80문항)
- `results/` — 실행 결과 원본 (gitignore). 요약표만 `docs/`와 README로 옮긴다.

## 골든셋 CSV 컬럼 (3주차에 확정)

| 컬럼 | 설명 |
| --- | --- |
| id | Q001 … |
| question | 실제 말투의 질문 |
| expected_answer | 기대 답 |
| evidence_ids | 근거 조문 청크 ID (여러 개면 `;`) |
| type | 약관 / 법규 / 종합 / 사례 / 거절 / 지표 / 권한 |
| difficulty | 상·중·하 |
| should_refuse | true/false |
| role | 질문자 역할 (7주차 권한 테스트용) |
