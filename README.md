# 通膨敏感度研究：解讀 · 方法 · 工具

對 AQR《Alternative Thinking 2026 Issue 3: Inflation Redux? Real Solutions for Real Returns》
（Hecht、Ilmanen、Maloney、McQuinn）的解讀與補充分析，含三個分頁：

- **報告解讀** —— 逐層拆解那張四象限圖在量什麼、結論是什麼、哪些地方需要打折扣
- **方法系統圖** —— 把整套分析方法拆成五個階段
- **宏觀敏感度工具** —— 用公開數據按同樣方法重算，內建 18 項真實歷史序列
- **數據監控看板** —— 本站用到的宏觀序列，取自 FRED，每日自動更新

原報告：<https://www.aqr.com/-/media/AQR/Documents/Alternative-Thinking/AQR-Alternative-Thinking-Q3-2026---Inflation-Redux.pdf>

線上版本：<https://zachwang181.github.io/inflation-sensitivity/>

## 數據更新

`data/macro.json` 由 `.github/workflows/update-macro.yml` 每日 UTC 12:00 自動更新：
跑 `scripts/fetch_macro.py` 從 FRED 抓 12 個序列，算出年增率與通膨新聞 z 值，有變化才提交。
也可以在 Actions 頁面手動觸發，或本地跑 `python3 scripts/fetch_macro.py`。

FRED 的 `fredgraph.csv` 端點不需要 API 金鑰，但一次請求多個序列會回傳 ZIP，所以腳本逐一抓取。
該端點也沒有 CORS 標頭，瀏覽器無法直接取用 —— 這正是改用 Actions 預抓進 repo 的原因。

## 部署

GitHub Pages，根目錄直出 `index.html`。單文件、無構建步驟、無外部 JS 依賴。

字體以非阻塞方式載入（`media="print"` + `onload`），Google Fonts 不可達時直接回退系統字體，頁面不會卡住。

僅供研究參考，不構成投資建議。
