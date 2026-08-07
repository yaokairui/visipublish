## Why

运营看板回答了「卖得怎么样」（GMV / 退款 / ROI），但没有回答「为什么」——差评里最集中的痛点（质量、物流、描述不符、售后）目前只能靠人工逐条翻。市面上的评价分析（Shulex VOC、京东评价 API 方案等）多为 SaaS 且要求数据上传；本项目坚持「本地优先」，分析自己的评价数据、不上传任何服务器。

## What Changes

- 新增 `reviews/` 应用（与 `dashboard/`、`frontend/` 平级）：FastAPI 分析后端 + 静态前端看板，端口 8503。
- **数据入口**：上传商家后台导出的评价 Excel/CSV + 粘贴文本；自动列映射、清洗、去重。
- **情感分析 analyzer 可插拔**：`lexicon`（默认，jieba + 电商情感词典，离线零重依赖）/ `huggingface`（可选，本地 RoBERTa）/ `llm`（可选，OpenAI 兼容 API，细粒度维度标签）。
- **痛点挖掘**：好评/差评分组 TF-IDF 对比 + 高频词统计，输出痛点词与例句。
- **看板**：情感分布、差评率趋势、平台/商品维度对比、痛点词云、差评明细表。
- **合规边界**：只分析用户自有评价数据；不做公共页面爬取，不接需企业资质的开放平台 API。

## Capabilities

### New Capabilities
- `review-import`: 评价数据导入与标准化（Excel/CSV/粘贴文本，列映射、清洗、去重）。
- `sentiment-analysis`: 情感分析 analyzer 接口与 lexicon / huggingface / llm 三种实现。
- `pain-point-mining`: 差评痛点挖掘（分词、停用词、好评差评 TF-IDF 对比、痛点词与例句）。
- `review-dashboard`: 评价分析看板（FastAPI 托管静态前端，ECharts 可视化，筛选联动）。

### Modified Capabilities
<!-- 无：不修改现有 batch-listing / channel-adapters / vision-recognition，也不动 dashboard/ 与 frontend/ -->

## Impact

- 新增目录：`reviews/backend/`（FastAPI + 分析模块）、`reviews/frontend/`（静态页，由后端托管）、`openspec/specs/review-*`。
- 新增依赖：`jieba`、情感词典（内置）；可选 `torch` + `transformers`、OpenAI 兼容客户端。
- 复用：`src/config.py` 的 API key 读取约定（新增 `REVIEW_LLM_KEY` / `REVIEW_LLM_BASE` / `REVIEW_LLM_MODEL` / `ANALYZER`）；前端设计令牌与 `frontend/` 一致（primary `#0F172A` / accent `#16A34A` / bg `#020617`）。
- 冒烟测试：新增 `scripts/reviews_smoke.py`（Playwright，1440px / 375px）。
