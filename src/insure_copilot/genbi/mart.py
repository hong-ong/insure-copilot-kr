"""가상 설계사·계약·교육 데이터 마트(DuckDB, 스타 스키마)를 만든다.

모든 데이터는 Faker와 고정 시드로 만든 가상 데이터다. 같은 시드면 언제 만들어도 같은 숫자가 나온다
(데모 영상·골든셋의 지표 정답이 바뀌지 않게).

    dim_branch  ─┐
    dim_agent   ─┼─ fact_contract (계약 1건 = 1행)
    dim_product ─┘   fact_training (교육 이수 1건 = 1행)
    dim_date
"""

from __future__ import annotations

import csv
import random
import tempfile
from datetime import date, timedelta
from pathlib import Path

import duckdb

SEED = 42
BRANCHES = [
    "강남",
    "종로",
    "분당",
    "부산서면",
    "대구동성로",
    "광주상무",
    "대전둔산",
    "인천구월",
    "수원영통",
    "일산",
]
PRODUCTS = [
    ("P01", "실손의료비", "건강"),
    ("P02", "질병보장", "건강"),
    ("P03", "암보장", "건강"),
    ("P04", "종신", "사망"),
    ("P05", "어린이", "건강"),
    ("P06", "연금", "저축"),
]
START, END = date(2024, 7, 1), date(2026, 10, 15)
N_AGENTS, N_CONTRACTS = 300, 10000
TRAINING_REQUIRED_HOURS = 12  # 연간 보수교육 의무 시간(가상 기준)


def build_mart(path: str | Path) -> Path:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    from faker import Faker

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    rng = random.Random(SEED)
    fake = Faker("ko_KR")
    Faker.seed(SEED)

    branches = [(f"B{i + 1:02d}", name) for i, name in enumerate(BRANCHES)]
    agents = []
    for i in range(N_AGENTS):
        branch_id = branches[i % len(branches)][0]
        career = rng.choice([0, 1, 1, 2, 3, 4, 5, 7, 10, 15])
        registered = END - timedelta(days=int(career * 365 + rng.randint(0, 300)))
        agents.append(
            (
                f"A{i + 1:04d}",
                fake.name(),
                branch_id,
                "전속" if rng.random() < 0.7 else "GA",
                career,
                registered,
                rng.random(),  # 숨은 '성실도' — 유지율·이수율·불완전판매에 영향을 줘서 현실적인 분포를 만든다
            )
        )

    contracts = []
    days = (END - START).days
    cum_weights, total = [], 0.0
    for ag in agents:
        total += 0.5 + ag[6]
        cum_weights.append(total)
    for i in range(N_CONTRACTS):
        a = rng.choices(agents, cum_weights=cum_weights)[0]
        diligence = a[6]
        d = START + timedelta(days=rng.randint(0, days))
        product = rng.choices(PRODUCTS, weights=[30, 20, 15, 10, 15, 10])[0]
        premium = {
            "P01": rng.randint(15, 60),
            "P02": rng.randint(40, 120),
            "P03": rng.randint(30, 90),
            "P04": rng.randint(100, 300),
            "P05": rng.randint(20, 70),
            "P06": rng.randint(100, 500),
        }[product[0]] * 1000
        withdrawn = rng.random() < 0.035 + (1 - diligence) * 0.03
        mis_sold = (not withdrawn) and rng.random() < 0.004 + (1 - diligence) * 0.012
        matured_13 = (d + timedelta(days=395)) <= END
        retained_13 = None
        if matured_13 and not withdrawn:
            retained_13 = (not mis_sold) and rng.random() < 0.72 + diligence * 0.22
        contracts.append(
            (f"C{i + 1:05d}", a[0], product[0], d, premium, withdrawn, mis_sold, retained_13)
        )

    trainings = []
    courses = [
        "불완전판매 예방",
        "금융소비자보호법",
        "개인정보보호",
        "상품 이해(실손)",
        "윤리·준법",
        "AI 기본법 이해",
    ]
    for a in agents:
        for year in (2025, 2026):
            target_hours = (
                TRAINING_REQUIRED_HOURS
                if rng.random() < 0.55 + a[6] * 0.42
                else rng.choice([3, 6, 9])
            )
            done, n = 0, 0
            while done < target_hours:
                hours = rng.choice([2, 3, 3, 4])
                completed = date(
                    year, rng.randint(1, 12 if year == 2025 else 9), rng.randint(1, 28)
                )
                trainings.append(
                    (f"T{len(trainings) + 1:06d}", a[0], rng.choice(courses), hours, completed)
                )
                done += hours
                n += 1

    con = duckdb.connect(str(path))
    con.execute("create table dim_branch (branch_id varchar primary key, branch_name varchar)")
    _bulk(con, "dim_branch", branches)
    con.execute(
        "create table dim_agent (agent_id varchar primary key, agent_name varchar, branch_id varchar, "
        "channel varchar, career_years integer, registered_at date)"
    )
    _bulk(con, "dim_agent", [a[:6] for a in agents])
    con.execute(
        "create table dim_product (product_id varchar primary key, product_name varchar, product_line varchar)"
    )
    _bulk(con, "dim_product", PRODUCTS)
    con.execute(
        "create table fact_contract (contract_id varchar primary key, agent_id varchar, product_id varchar, "
        "contract_date date, monthly_premium integer, withdrawn boolean, mis_sold boolean, retained_13 boolean)"
    )
    _bulk(con, "fact_contract", contracts)
    con.execute(
        "create table fact_training (training_id varchar primary key, agent_id varchar, course_name varchar, "
        "hours integer, completed_date date)"
    )
    _bulk(con, "fact_training", trainings)
    con.execute(
        "create table dim_date as select d::date as date, year(d) as year, quarter(d) as quarter, "
        "month(d) as month, strftime(d, '%Y-%m') as year_month "
        f"from range(date '{START}', date '{END}' + interval 1 day, interval 1 day) t(d)"
    )
    con.close()
    return path


def _bulk(con: duckdb.DuckDBPyConnection, table: str, rows: list[tuple]) -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    # executemany는 한 행씩 넣어 느리다 → 임시 CSV로 쓰고 한 번에 읽어 들인다
    with tempfile.NamedTemporaryFile(
        "w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    ) as f:
        csv.writer(f).writerows(("" if v is None else v for v in r) for r in rows)
        tmp = f.name
    try:
        con.execute(
            f"insert into {table} select * from read_csv('{Path(tmp).as_posix()}', "
            "header = false, all_varchar = true, nullstr = '')"
        )
    finally:
        Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    from insure_copilot.config import settings

    print(build_mart(settings.mart_path))
