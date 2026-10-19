"""GenBI: 자연어 지표 질문 → (LLM이 지표·차원·기간만 고름) → 템플릿 SQL → DuckDB 계산.

LLM에게 SQL을 직접 쓰게 하지 않는다(Text-to-SQL은 틀려도 그럴듯한 숫자를 낸다).
LLM은 metrics.yaml에 정의된 지표 key 중 하나를 고르는 일만 하고, 계산은 정의된 SQL이 한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

import duckdb
import yaml

from insure_copilot.config import settings
from insure_copilot.llm.gateway import LLMResult, complete_json

METRICS_PATH = Path(__file__).with_name("metrics.yaml")

DIMENSIONS = {
    "none": ("'전체'", ""),
    "branch": ("b.branch_name", "join dim_branch b on b.branch_id = a.branch_id"),
    "channel": ("a.channel", ""),
    "product": ("p.product_name", "join dim_product p on p.product_id = c.product_id"),
    "month": ("strftime(c.contract_date, '%Y-%m')", ""),
    "agent": ("a.agent_name || ' (' || a.agent_id || ')'", ""),
}
DIM_LABELS = {
    "none": "전체",
    "branch": "지점별",
    "channel": "채널별",
    "product": "상품별",
    "month": "월별",
    "agent": "설계사별",
}

SELECT_PROMPT = """보험사 지표 질문을 정해진 지표 카탈로그에 매핑하세요. SQL은 쓰지 마세요.

지표 카탈로그:
{catalog}

차원(group_by): none(전체 한 숫자) / branch(지점별) / channel(전속·GA) / product(상품별) / month(월별) / agent(설계사별)
오늘: {today}. 데이터는 2024-07-01 ~ 2026-10-15 범위입니다.
기간 해석 예: "이번 분기" = 올해 현재 분기 시작일~오늘, "지난 분기" = 직전 분기 전체, 기간 언급이 없으면 최근 3개월.

카탈로그에 없는 지표면 metric 을 null 로 두세요.
JSON으로만 답하세요:
{{"metric": "key 또는 null", "group_by": "none", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "period_label": "2026년 3분기"}}
"""


@lru_cache(maxsize=1)
def load_metrics() -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return yaml.safe_load(METRICS_PATH.read_text(encoding="utf-8"))["metrics"]


@lru_cache(maxsize=1)
def _connect() -> duckdb.DuckDBPyConnection:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    path = Path(settings.mart_path)
    if not path.exists():
        from insure_copilot.genbi.mart import build_mart

        build_mart(path)
    return duckdb.connect(str(path), read_only=True)


@dataclass
class MetricAnswer:
    """지표 계산 결과."""

    content: str
    llm: LLMResult | None
    meta: dict = field(default_factory=dict)
    ok: bool = True


def scope_for(profile: dict) -> tuple[str, str, bool]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # 행 단위 권한: 설계사 = 본인 실적만 / 본사(법무·AX) = 전사 + 설계사별 상세 / 그 외 팀원 = 전사 집계(개인별 상세 불가)
    if profile.get("role") == "agent":
        code = (profile.get("agent_code") or "A0001").replace("'", "")
        return f"a.agent_id = '{code}'", "본인", False
    if profile.get("role") in ("legal", "ax_admin"):
        return "true", "전사", True
    return "true", "전사", False


def answer_metric(question: str, profile: dict) -> MetricAnswer:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    metrics = load_metrics()
    catalog = "\n".join(
        f"- {k}: {m['label']} — {m['definition']} (허용 차원: {', '.join(m['allowed_dims'])})"
        for k, m in metrics.items()
    )
    choice, result = complete_json(
        [
            {
                "role": "system",
                "content": SELECT_PROMPT.format(catalog=catalog, today=date.today().isoformat()),
            },
            {"role": "user", "content": question},
        ],
        trace_name="genbi_select",
        max_tokens=200,
    )
    key = choice.get("metric")
    if key not in metrics:
        names = ", ".join(m["label"] for m in metrics.values())
        return MetricAnswer(
            content=f"아직 정의되지 않은 지표예요. 지금 조회할 수 있는 지표는 **{names}** 입니다.",
            llm=result,
            ok=False,
            meta={"selection": choice},
        )

    metric = metrics[key]
    scope_sql, scope_label, can_drill = scope_for(profile)
    group_by = choice.get("group_by") or "none"
    notes = []
    if group_by == "agent" and not can_drill:
        group_by, notes = (
            "none",
            ["설계사별 상세는 본사 권한에서만 볼 수 있어 전체 값으로 보여 드려요."],
        )
    if group_by not in ("none", *metric["allowed_dims"]) or group_by not in DIMENSIONS:
        notes.append(
            f"'{DIM_LABELS.get(group_by, group_by)}' 구분은 이 지표에서 지원하지 않아 전체 값으로 보여 드려요."
        )
        group_by = "none"

    start, end = choice.get("start") or "2026-07-01", choice.get("end") or date.today().isoformat()
    try:
        date.fromisoformat(start)
        date.fromisoformat(end)
    except ValueError:
        start, end = "2026-07-01", date.today().isoformat()
    dim, dim_join = DIMENSIONS[group_by]
    sql = metric["sql"].format(start=start, end=end, scope=scope_sql, dim=dim, dim_join=dim_join)
    rows = _connect().execute(sql).fetchall()

    unit = metric["unit"]
    fmt = (lambda v: f"{v:.1f}%") if unit == "percent" else (lambda v: f"{v:.2f}건")
    period_label = choice.get("period_label") or f"{start} ~ {end}"
    table = [
        {"dim": r[0], "value": round(float(r[1] or 0), 2), "base": int(r[2] or 0)} for r in rows
    ]
    if not table:
        content = f"**{metric['label']}** · {period_label} · {scope_label}\n\n해당 기간에 계산할 데이터가 없어요."
    elif group_by == "none":
        content = (
            f"**{metric['label']}** · {period_label} · {scope_label} 기준\n\n"
            f"## {fmt(table[0]['value'])}\n\n산출 대상 {table[0]['base']:,}"
            + ("건" if metric["grain"].startswith("계약") else "명")
        )
    else:
        lines = "\n".join(f"| {r['dim']} | {fmt(r['value'])} | {r['base']:,} |" for r in table)
        content = (
            f"**{metric['label']}** · {period_label} · {scope_label} · {DIM_LABELS[group_by]}\n\n"
            f"| 구분 | 값 | 산출 대상 |\n| --- | --- | --- |\n{lines}"
        )
    if notes:
        content += "\n\n" + "\n".join(f"ℹ️ {n}" for n in notes)
    return MetricAnswer(
        content=content,
        llm=result,
        meta={
            "metric": key,
            "label": metric["label"],
            "definition": metric["definition"],
            "owner": metric.get("owner"),
            "unit": unit,
            "group_by": group_by,
            "period": {"start": start, "end": end, "label": period_label},
            "scope": scope_label,
            "rows": table,
            "sql": sql.strip(),
            "selection": json.loads(json.dumps(choice, ensure_ascii=False, default=str)),
        },
    )
