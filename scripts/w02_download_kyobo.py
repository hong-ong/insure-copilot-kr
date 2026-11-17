# 2주차 — 교보생명 공시실 "전체상품조회"의 모든 상품 · 모든 판매기간별 약관 내려받기
#
# 출처: https://www.kyobo.com/dgt/web/product-official/all-product/search
# 화면이 부르는 공개 API 두 개와 파일 다운로드 주소를 그대로 쓴다 (로그인 불필요, robots.txt 제한 없음).
#   1) POST /dtc/product-official/find-allProductSearch        → 상품 목록
#   2) POST /dtc/product-official/find-allProductSearchDetail  → 상품별 판매기간 + 파일명
#   3) GET  /file/ajax/download?fName=/dtc/pdf/mm/<파일명>      → PDF
#
# 원문은 커밋하지 않는다(data/raw/ 는 gitignore). 받은 결과는 data/SOURCES.md 에 기록한다.
#
# 사용법
#   uv run python scripts/w02_download_kyobo.py index                 # 목록(manifest.jsonl)만 만든다
#   uv run python scripts/w02_download_kyobo.py download              # 약관 PDF를 받는다 (이어받기 가능)
#   uv run python scripts/w02_download_kyobo.py download --kinds terms,summary,method
#   uv run python scripts/w02_download_kyobo.py download --out E:\kyobo   # 다른 드라이브에 저장
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = "https://www.kyobo.com"
PAGE = f"{BASE}/dgt/web/product-official/all-product/search"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "kyobo"

# 상세 응답(list2)의 칸 이름 → 문서 종류. temp01은 상품요약서(퇴직연금·퇴직보험은 계약서)다.
KINDS = {"terms": "temp02", "summary": "temp01", "method": "temp03"}
CATEGORY = {
    "PAMS01": "교육보험", "PAMS02": "연금보험", "PAMS03": "저축보험", "PAMS04": "보장성보험",
    "PAMS05": "기업보험", "PAMS06": "통신판매전용상품", "PAMS07": "방카슈랑스전용상품",
    "PAMS08": "퇴직연금", "PAMS09": "퇴직보험", "PAMS10": "온라인보험",
}


def _request(url: str, body: dict | None = None, retries: int = 4) -> bytes:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    headers = {"User-Agent": UA, "Referer": PAGE}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=UTF-8"
        headers["X-Requested-With"] = "XMLHttpRequest"
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as res:
                return res.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == retries:  # 404는 서버에 파일이 없는 것 — 다시 해도 같다
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == retries:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def _api(path: str, body: dict) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    res = json.loads(_request(BASE + path, body))
    if res["header"]["code"] != "SUCCESS":
        raise RuntimeError(f"{path}: {res['header']}")
    return res["body"]


def fetch_products() -> list[dict]:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    products: list[dict] = []
    page = 1
    while True:
        body = _api("/dtc/product-official/find-allProductSearch", {
            "dgtPdtAtrDvCd": "M", "dgtPdtAtrLclCd": "", "dgtPdtAtrMclCd": "99", "dgtPdtAtrSmclCd": "99",
            "saleYn": "99", "dgtMseAddiPsYn": "", "searchTxt": "",
            "currentPage": page, "pagePerSize": 100, "pageNumber": 10, "deviceDv": "pc",
        })
        products += body["list"]
        print(f"  목록 {page}/{body['pageInfo']['totPageCnt']}쪽 (누적 {len(products)}/{body['listCnt']})", flush=True)
        if page >= body["pageInfo"]["totPageCnt"]:
            return products
        page += 1
        time.sleep(0.3)


def fetch_periods(product: dict) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    body = _api("/dtc/product-official/find-allProductSearchDetail", {"dgtPdtPdSeqtId": str(product["dgtPdtAtrSeqtId"])})
    periods = []
    for period, files in zip(body["list"], body["list2"]):
        end = period.get("saleEdDt")
        periods.append({
            "period_id": period.get("dgtPdtPdSeqtId"),
            "sale_start": period.get("saleStDt"),
            "sale_end": None if end in (None, "", "0001-01-01 BC") else end,
            **{kind: files.get(col) or None for kind, col in KINDS.items()},
        })
    return {
        "product_id": product["dgtPdtAtrSeqtId"],
        "product_code": product.get("dgtPdtCd"),
        "name": product.get("dgtPdtAtrNm") or "",
        "category": CATEGORY.get(product.get("dgtPdtAtrMclCd") or "", ""),
        "category_code": product.get("dgtPdtAtrMclCd"),
        "sub_category_code": product.get("dgtPdtAtrSmclCd"),
        "on_sale": product.get("saleYn") == "Y",
        "periods": periods,
    }


def build_index(out: Path) -> Path:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    out.mkdir(parents=True, exist_ok=True)
    products = fetch_products()
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = []
        for i, row in enumerate(pool.map(fetch_periods, products), 1):
            rows.append(row)
            if i % 100 == 0 or i == len(products):
                print(f"  판매기간 조회 {i}/{len(products)}", flush=True)
    manifest = out / "manifest.jsonl"
    manifest.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    n_periods = sum(len(r["periods"]) for r in rows)
    print(f"상품 {len(rows)}개 · 판매기간 {n_periods}개 → {manifest}")
    for kind in KINDS:
        names = {p[kind] for r in rows for p in r["periods"] if p[kind]}
        print(f"  {kind}: 파일명 있는 기간 {sum(1 for r in rows for p in r['periods'] if p[kind])}개, 고유 파일 {len(names)}개")
    return manifest


def _local_name(server_name: str) -> str:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    return re.sub(r'[\\/:*?"<>|]', "_", server_name).strip()


def download_one(server_name: str, dest: Path) -> dict:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    if dest.exists() and dest.stat().st_size > 0:
        return {"file": server_name, "status": "skip", "bytes": dest.stat().st_size}
    # 화면 코드의 encodeURI 와 같은 방식으로 한 번만 인코딩한다 (두 번 하면 404).
    url = f"{BASE}/file/ajax/download?fName=/dtc/pdf/mm/" + urllib.parse.quote(server_name, safe="()~!*'._-,;@&=+$#")
    try:
        data = _request(url)
    except urllib.error.HTTPError as e:
        return {"file": server_name, "status": f"http_{e.code}", "bytes": 0}
    except Exception as e:  # noqa: BLE001 — 한 파일 실패가 전체를 멈추지 않게 기록만 한다
        return {"file": server_name, "status": f"error:{type(e).__name__}", "bytes": 0}
    if not data.startswith(b"%PDF") and server_name.lower().endswith(".pdf"):
        return {"file": server_name, "status": "not_pdf", "bytes": len(data)}
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return {"file": server_name, "status": "ok", "bytes": len(data)}


def download_all(out: Path, kinds: list[str], workers: int, limit: int | None) -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    manifest = out / "manifest.jsonl"
    if not manifest.exists():
        build_index(out)
    rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line]
    jobs: dict[Path, str] = {}
    for kind in kinds:
        (out / kind).mkdir(parents=True, exist_ok=True)
        for r in rows:
            for p in r["periods"]:
                if p.get(kind):
                    jobs.setdefault(out / kind / _local_name(p[kind]), p[kind])
    items = list(jobs.items())[:limit]
    print(f"받을 파일 {len(items)}개 ({', '.join(kinds)}) → {out}")

    counts: dict[str, int] = {}
    total = 0
    started = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool, (out / "download_log.jsonl").open("a", encoding="utf-8") as log:
        for i, res in enumerate(pool.map(lambda kv: download_one(kv[1], kv[0]), items), 1):
            counts[res["status"]] = counts.get(res["status"], 0) + 1
            total += res["bytes"]
            if res["status"] != "skip":
                log.write(json.dumps(res, ensure_ascii=False) + "\n")
            if i % 50 == 0 or i == len(items):
                print(f"  {i}/{len(items)} · {total / 1e6:,.0f} MB · {time.time() - started:,.0f}초 · {counts}", flush=True)
    print(f"끝. {counts}, 합계 {total / 1e9:.2f} GB")


def main() -> None:
    """TODO(재홍): 무엇을 왜 하는가 한 문장"""
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="교보생명 전체상품 기간별 약관 내려받기")
    ap.add_argument("command", choices=["index", "download"])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="저장 폴더 (기본 data/raw/kyobo)")
    ap.add_argument("--kinds", default="terms", help="terms(약관), summary(상품요약서), method(사업방법서) 쉼표 구분")
    ap.add_argument("--workers", type=int, default=3, help="동시에 받는 파일 수 (서버 부담을 줄이려 작게 둔다)")
    ap.add_argument("--limit", type=int, default=None, help="앞에서 N개만 받기 (시험용)")
    args = ap.parse_args()
    if args.command == "index":
        build_index(args.out)
    else:
        kinds = [k.strip() for k in args.kinds.split(",") if k.strip()]
        unknown = set(kinds) - set(KINDS)
        if unknown:
            ap.error(f"모르는 종류: {unknown}")
        download_all(args.out, kinds, args.workers, args.limit)


if __name__ == "__main__":
    main()
