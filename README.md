# 通胀敏感度研究：解读 · 方法 · 工具

对 AQR《Alternative Thinking 2026 Issue 3: Inflation Redux? Real Solutions for Real Returns》
（Hecht、Ilmanen、Maloney、McQuinn）的解读与补充分析，含三个分页：

- **报告解读** —— 逐层拆解那张四象限图在量什么、结论是什么、哪些地方需要打折扣
- **方法系统图** —— 把整套分析方法拆成五个阶段
- **宏观敏感度工具** —— 用公开数据按同样方法重算，内建 18 项真实历史序列
- **数据监控看板** —— 本站用到的宏观序列，取自 FRED，每日自动更新

原报告：<https://www.aqr.com/-/media/AQR/Documents/Alternative-Thinking/AQR-Alternative-Thinking-Q3-2026---Inflation-Redux.pdf>

线上版本：<https://zachwang181.github.io/inflation-sensitivity/>

## 数据更新

`data/macro.json` 由 `.github/workflows/update-macro.yml` 每日 UTC 12:00 自动更新：
跑 `scripts/fetch_macro.py` 从 FRED 抓 12 个序列，算出同比与通胀新闻 z 值，有变化才提交。
也可以在 Actions 页面手动触发，或本地跑 `python3 scripts/fetch_macro.py`。

FRED 的 `fredgraph.csv` 端点不需要 API 金钥，但一次请求多个序列会回传 ZIP，所以脚本逐一抓取。
该端点也没有 CORS 标头，浏览器无法直接取用 —— 这正是改用 Actions 预抓进 repo 的原因。

## 部署

GitHub Pages，根目录直出 `index.html`。单文件、无构建步骤、无外部 JS 依赖。

字体以非阻塞方式载入（`media="print"` + `onload`），Google Fonts 不可达时直接回退系统字体，页面不会卡住。

仅供研究参考，不构成投资建议。
