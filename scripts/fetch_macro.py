#!/usr/bin/env python3
"""從 FRED 抓宏觀序列，算出年增率與通膨新聞 z 值，寫成 data/macro.json。

只用標準庫。FRED 的 fredgraph.csv 端點不需要 API 金鑰，但一次要多個序列
會回傳 ZIP，所以逐一抓取。
"""
import json, csv, io, os, sys, urllib.request, datetime, statistics

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd=1960-01-01"

SERIES = [
    # id,          中文名,            單位,   類型（idx＝指數要算年增率；rate＝本身就是%；px＝價格）
    ("CPIAUCSL",   "CPI 全項",        "%",   "idx"),
    ("CPILFESL",   "核心 CPI",        "%",   "idx"),
    ("PCEPI",      "PCE 物價",        "%",   "idx"),
    ("PCEPILFE",   "核心 PCE",        "%",   "idx"),
    ("T5YIE",      "5 年期通膨預期",   "%",   "rate"),
    ("T10YIE",     "10 年期通膨預期",  "%",   "rate"),
    ("DGS10",      "10 年期公債殖利率", "%",   "rate"),
    ("DFII10",     "10 年期實質利率",  "%",   "rate"),
    ("FEDFUNDS",   "聯邦基金利率",     "%",   "rate"),
    ("UNRATE",     "失業率",          "%",   "rate"),
    ("GDPC1",      "實質 GDP",        "%",   "idx"),
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

def detect_freq(obs, compressed):
    """回傳 (顯示頻率, 原始是否為日頻)。"""
    daily = len(obs) > len(compressed) * 1.5
    gaps = []
    for i in range(max(1, len(compressed) - 25), len(compressed)):
        a, b = compressed[i - 1][0], compressed[i][0]
        gaps.append((int(b[:4]) - int(a[:4])) * 12 + int(b[5:7]) - int(a[5:7]))
    q = sorted(gaps)[len(gaps) // 2] if gaps else 1
    return ("Q" if q >= 3 else "M"), daily

def fmt_period(d, freq):
    """季頻顯示成 2026 Q2，月頻原樣。"""
    if freq != "Q":
        return d
    return f"{d[:4]} Q{(int(d[5:7]) - 1) // 3 + 1}"

def yoy(series):
    """年增率變化率，依序列頻率自動判斷回看幾期。"""
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
            raw = fetch(sid)
            obs = monthly(raw)
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
        freq, from_daily = detect_freq(raw, obs)
        result[sid] = {
            "name": name, "unit": unit, "kind": kind,
            "freq": freq, "fromDaily": from_daily,
            "latest": {"date": last_d, "period": fmt_period(last_d, freq),
                       "value": round(last_v, 3),
                       "chg": round(last_v - prev_v, 3) if prev_v is not None else None,
                       "chgYr": round(last_v - yr_ago, 3) if yr_ago is not None else None},
            "levelLatest": round(level[-1][1], 3),
            # 只留近 15 年供走勢圖，控制檔案大小
            "hist": [[d, round(v, 3)] for d, v in display if d >= "2011-01"],
        }
        print(f"  ✓ {sid:<12} {fmt_period(last_d, freq):<9} {last_v:>8.2f}  "
              f"（{len(display)} 期 · {'季頻' if freq == 'Q' else '月頻'}"
              f"{' · 原始日頻' if from_daily else ''}）")

    # 通膨新聞：年增率 CPI − 12 個月前的年增率 CPI，與研究頁的方法一致
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
                    "regime": "上行衝擊" if z > 1 else ("下行衝擊" if z < -1 else "穩定"),
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

    # 只有資料真的變了才寫檔。updated 是執行時間戳，每次都會變，
    # 若連它一起比對，工作流的「有變化才提交」就永遠成立、天天產生空更新。
    if os.path.exists(path):
        try:
            with io.open(path, encoding="utf-8") as f:
                prev = json.load(f)
            a = {k: v for k, v in prev.items() if k != "updated"}
            b = {k: v for k, v in out.items() if k != "updated"}
            if a == b:
                print(f"\n資料與現有檔案相同（最後更新 {prev.get('updated')}），不寫檔")
                return 0
        except Exception:
            pass  # 舊檔壞掉就直接覆寫

    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n寫入 {len(result)}/{len(SERIES)} 個序列 · {os.path.getsize(path)/1024:.1f} KB"
          + (f" · {len(errors)} 個失敗" if errors else ""))
    return 1 if len(result) < len(SERIES) // 2 else 0

if __name__ == "__main__":
    sys.exit(main())
