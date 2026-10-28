"""가상 마트와 지표 SQL 템플릿이 모든 허용 차원에서 실행되는지 (LLM 없이)."""

import duckdb

from insure_copilot.genbi.engine import DIMENSIONS, load_metrics, scope_for
from insure_copilot.genbi.mart import build_mart


def test_all_metrics_run_on_all_allowed_dims(tmp_path):
    path = build_mart(tmp_path / "mart.duckdb")
    con = duckdb.connect(str(path), read_only=True)
    for key, metric in load_metrics().items():
        for dim_key in ["none", *metric["allowed_dims"]]:
            dim, join = DIMENSIONS[dim_key]
            for profile in ({"role": "agent", "agent_code": "A0007"}, {"role": "legal"}):
                scope, _, _ = scope_for(profile)
                sql = metric["sql"].format(
                    start="2026-01-01", end="2026-09-30", scope=scope, dim=dim, dim_join=join
                )
                rows = con.execute(sql).fetchall()
                assert rows, (key, dim_key, profile)
                for _, value, base in rows:
                    assert value is None or value >= 0
                    assert base >= 0


def test_mart_is_deterministic(tmp_path):
    a = build_mart(tmp_path / "a.duckdb")
    b = build_mart(tmp_path / "b.duckdb")
    q = "select count(*), sum(monthly_premium) from fact_contract"
    assert (
        duckdb.connect(str(a)).execute(q).fetchone() == duckdb.connect(str(b)).execute(q).fetchone()
    )
