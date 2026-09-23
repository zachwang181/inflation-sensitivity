#!/usr/bin/env python3
"""從 FRED 抓宏觀序列，算出同比與通脹新聞 z 值，寫成 data/macro.json。

只用標準庫。FRED 的 fredgraph.csv 端點不需要 API 金鑰，但一次要多個序列
會回傳 ZIP，所以逐一抓取。
"""
import json, csv, io, os, sys, urllib.request, datetime, statistics

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd=1960-01-01"

SERIES = [
    # id,          中文名,            單位,   類型（idx＝指數要算同比；rate＝本身就是%；px＝價格）
    ("CPIAUCSL",   "CPI 全项",        "%",   "idx"),
    ("CPILFESL",   "核心 CPI",        "%",   "idx"),
    ("PCEPI",      "PCE 物价",        "%",   "idx"),
    ("PCEPILFE",   "核心 PCE",        "%",   "idx"),
    ("T5YIE",      "5 年期通胀预期",   "%",   "rate"),
    ("T10YIE",     "10 年期通胀预期",  "%",   "rate"),
    ("DGS10",      "10 年期国债收益率", "%",   "rate"),
    ("DFII10",     "10 年期实际利率",  "%",   "rate"),
    ("FEDFUNDS",   "联邦基金利率",     "%",   "rate"),
    ("UNRATE",     "失业率",          "%",   "rate"),
    ("GDPC1",      "实际 GDP",        "%",   "idx"),
    ("DCOILWTICO", "WTI 原油",        "美元", "px"),
]

def fetch(sid):
    req = urllib.request.Request(FRED.format(sid), headers={"User-Agent": "macro-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
    if raw[:2] == b"PK":
        raise RuntimeError(f"{sid}: 收到 ZIP 而非 CSV")
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
    out = []
    for d, v in ((r[0], r[1]) for r in rows[1:] if len(r) >= 2):
        if v in ("", "."):
            continue
        out.append((d, float(v)))
    if not out:
        raise RuntimeError(f"{sid}: 沒有有效觀測值")
    return out

def monthly(obs):
    """日頻壓成月頻（取當月最後一筆），月頻與季頻原樣保留。"""
    by = {}
    for d, v in obs:
        by[d[:7]] = v
    return sorted(by.items())

def yoy(series):
    """同比變化率，依序列頻率自動判斷回看幾期。"""
    m = dict(series)
    keys = [k for k, _ in series]
    out = []
    for k in keys:
        y, mo = int(k[:4]), int(k[5:7])
        prev = f"{y-1:04d}-{mo:02d}"
        if prev in m and m[prev]:
            out.append((k, (m[k] / m[prev] - 1) * 100))
    return out

def main():
    result, errors = {}, []
    for sid, name, unit, kind in SERIES:
        try:
            obs = monthly(fetch(sid))
        except Exception as e:
            errors.append(f"{sid}: {e}")
            print(f"  ✗ {sid}: {e}", file=sys.stderr)
            continue
        level = obs
        display = yoy(obs) if kind == "idx" else obs
        if not display:
            errors.append(f"{sid}: 無可顯示的序列")
            continue
        last_d, last_v = display[-1]
        prev_v = display[-2][1] if len(display) > 1 else None
        yr_ago = dict(display).get(f"{int(last_d[:4])-1:04d}-{last_d[5:7]}")
        result[sid] = {
            "name": name, "unit": unit, "kind": kind,
            "latest": {"date": last_d, "value": round(last_v, 3),
                       "chg": round(last_v - prev_v, 3) if prev_v is not None else None,
                       "chgYr": round(last_v - yr_ago, 3) if yr_ago is not None else None},
            "levelLatest": round(level[-1][1], 3),
            # 只留近 15 年供走勢圖，控制檔案大小
            "hist": [[d, round(v, 3)] for d, v in display if d >= "2011-01"],
        }
        print(f"  ✓ {sid:<12} {last_d}  {last_v:>8.2f}  （{len(display)} 期）")

    # 通脹新聞：同比 CPI − 12 個月前的同比 CPI，與研究頁的方法一致
    news = None
    if "CPIAUCSL" in result:
        full = yoy(monthly(fetch("CPIAUCSL")))
        m = dict(full)
        chg = []
        for k, v in full:
            prev = f"{int(k[:4])-1:04d}-{k[5:7]}"
            if prev in m:
                chg.append((k, v - m[prev]))
        if chg:
            vals = [v for _, v in chg]
            mu, sd = statistics.fmean(vals), statistics.pstdev(vals)
            z = (chg[-1][1] - mu) / sd if sd else 0
            news = {"date": chg[-1][0], "value": round(chg[-1][1], 3), "z": round(z, 2),
                    "mean": round(mu, 3), "sd": round(sd, 3),
                    "regime": "上行冲击" if z > 1 else ("下行冲击" if z < -1 else "稳定"),
                    "hist": [[d, round(v, 3)] for d, v in chg if d >= "2011-01"]}

    out = {
        "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "source": "Federal Reserve Bank of St. Louis (FRED)",
        "order": [s[0] for s in SERIES if s[0] in result],
        "series": result,
        "inflationNews": news,
        "errors": errors,
    }
    path = os.path.join(os.path.dirname(__file__), "..", "data", "macro.json")
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n寫入 {len(result)}/{len(SERIES)} 個序列 · {os.path.getsize(path)/1024:.1f} KB"
          + (f" · {len(errors)} 個失敗" if errors else ""))
    return 1 if len(result) < len(SERIES) // 2 else 0

if __name__ == "__main__":
    sys.exit(main())
