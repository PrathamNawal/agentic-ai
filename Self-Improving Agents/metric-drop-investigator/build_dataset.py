"""Build the compact daily dataset from the REAL CFPB consumer-complaints database.

Source: Hugging Face mirror BEE-spoke-data/consumer-finance-complaints (CC0, ~4.7M complaints,
2011-2024; original: consumerfinance.gov/data-research/consumer-complaints). The raw files are ~1.1 GB, so
this script is run once, offline, and writes a small snapshot that the app ships with:

    data/snapshots/complaints_daily.csv.gz   entity,date,dimension,segment,count
    data/snapshots/dataset_meta.json         provenance, row counts, date range, cutoff

    python build_dataset.py --cache /some/dir           # downloads shards (~1.1 GB) if missing
    python build_dataset.py --top 12 --since 2018-01-01

Aggregation: for the TOP-N companies by complaint volume since --since, daily complaint counts overall
('total') and split by product, issue, submission channel, company response, and timeliness.
Rare products/issues are folded into 'Other ...' to keep the table small.
"""
import argparse
import json
import urllib.request
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import requests

REPO = "BEE-spoke-data/consumer-finance-complaints"
HF = "https://huggingface.co"
COLS = ["Date received", "Company", "Product", "Issue", "Submitted via",
        "Company response to consumer", "Timely response?"]
OUT = Path(__file__).parent / "data" / "snapshots"


def shard_names() -> list[str]:
    req = urllib.request.Request(f"{HF}/api/datasets/{REPO}", headers={"User-Agent": "dataset-builder"})
    files = [s["rfilename"] for s in json.load(urllib.request.urlopen(req, timeout=30))["siblings"]]
    return sorted(f for f in files if f.startswith("data/") and f.endswith(".parquet"))


def fetch(name: str, cache: Path) -> Path:
    dest = cache / name.replace("/", "_")
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    print(f"downloading {name} ...", flush=True)
    with requests.get(f"{HF}/datasets/{REPO}/resolve/main/{name}", stream=True, timeout=120,
                      headers={"User-Agent": "dataset-builder"}) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def batches(path: Path, columns):
    for b in pq.ParquetFile(path).iter_batches(batch_size=250_000, columns=columns):
        yield b.to_pandas()


def main(cache: Path, top: int, since: str) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    files = [fetch(n, cache) for n in shard_names()]

    # pass 1: which companies matter? (top N by volume since `since`)
    company_totals: Counter = Counter()
    rows_total, dmin, dmax = 0, "9999", "0000"
    for f in files:
        for df in batches(f, ["Date received", "Company"]):
            rows_total += len(df)
            dmin, dmax = min(dmin, df["Date received"].min()), max(dmax, df["Date received"].max())
            recent = df[df["Date received"] >= since]
            company_totals.update(recent["Company"].value_counts().to_dict())
    entities = [c for c, _ in company_totals.most_common(top)]
    print(f"{rows_total:,} complaints, {dmin}..{dmax}; entities: {entities}", flush=True)

    # pass 2: counts for those companies. First find the common products/issues to keep.
    prod_c: Counter = Counter()
    issue_c: Counter = Counter()
    for f in files:
        for df in batches(f, ["Date received", "Company", "Product", "Issue"]):
            df = df[df["Company"].isin(entities) & (df["Date received"] >= since)]
            prod_c.update(df["Product"].value_counts().to_dict())
            issue_c.update(df["Issue"].value_counts().to_dict())
    keep_prod = {p for p, _ in prod_c.most_common(8)}
    keep_issue = {i for i, _ in issue_c.most_common(14)}

    frames = []
    for f in files:
        for df in batches(f, COLS):
            df = df[df["Company"].isin(entities) & (df["Date received"] >= since)].copy()
            if df.empty:
                continue
            df["Product"] = df["Product"].where(df["Product"].isin(keep_prod), "Other products")
            df["Issue"] = df["Issue"].where(df["Issue"].isin(keep_issue), "Other issues")
            df["Company response to consumer"] = df["Company response to consumer"].fillna("Unknown")
            df["Timely response?"] = df["Timely response?"].map({"Yes": "Timely", "No": "Untimely"}).fillna("Unknown")
            df["Submitted via"] = df["Submitted via"].fillna("Unknown")
            base = df.rename(columns={"Company": "entity", "Date received": "date"})
            parts = [base.assign(dimension="total", segment="all")]
            for dim, col in (("product", "Product"), ("issue", "Issue"), ("channel", "Submitted via"),
                             ("response", "Company response to consumer"), ("timely", "Timely response?")):
                parts.append(base.assign(dimension=dim, segment=base[col]))
            frames.append(pd.concat(parts)[["entity", "date", "dimension", "segment"]]
                          .value_counts().rename("count").reset_index())
    agg = (pd.concat(frames).groupby(["entity", "date", "dimension", "segment"], as_index=False)["count"].sum()
           .sort_values(["entity", "date", "dimension", "segment"]))

    # cutoff: the newest days are still being published/answered; use the last day whose volume looks complete
    tot = agg[agg.dimension == "total"].groupby("date")["count"].sum()
    tot.index = pd.to_datetime(tot.index)
    med = tot.tail(60).median()
    last_complete = max((d for d in tot.index if tot[d] >= 0.5 * med and d.dayofweek < 5 or d <= tot.index[-8]),
                        default=tot.index[-1])
    OUT.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUT / "complaints_daily.csv.gz", index=False)
    meta = {
        "source": f"{HF}/datasets/{REPO}", "original": "https://www.consumerfinance.gov/data-research/consumer-complaints/",
        "license": "CC0-1.0", "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "complaints_in_source": rows_total, "source_date_range": [dmin, dmax], "since": since,
        "entities": entities, "snapshot_rows": len(agg), "last_complete_date": str(last_complete.date()),
    }
    (OUT / "dataset_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path("/tmp/cfpb_cache"))
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--since", default="2018-01-01")
    a = ap.parse_args()
    main(a.cache, a.top, a.since)
