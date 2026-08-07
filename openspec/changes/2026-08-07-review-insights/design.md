## Context

现状（见 proposal.md - Why）：运营看板（`dashboard/`）是纯前端 Excel 导入看板；上架助手（`frontend/` + `webapp/`）是 React + FastAPI。评价分析补齐「为什么卖不动」的最后一环。

调研结论（2026-08）：
- **数据可得性**：拼多多商家后台「评价管理 → 导出」、淘宝千牛「评价管理」专业版支持批量导出 Excel；京东有第三方评价 API 服务（需资质/付费）。结论：用户自有评价数据可通过官方后台导出，无需爬虫。
- **合规**：2025 修订《反不正当竞争法》及司法案例认定「绕开风控批量爬取平台数据」构成不正当竞争并涉隐私；公共页面爬取不在本项目范围。
- **情感分析选型**：SnowNLP 轻量离线但词典陈旧（网络用语/emoji 易失准）；`uer/roberta-base-finetuned-jd-binary-chinese` 为京东评论二分类、离线质量好但需 torch（约 2GB）；LLM API 质量最高、支持维度标签但有成本。

## Goals / Non-Goals

**Goals:**
- 上传自己的评价数据 → 情感分布 + 差评痛点 + 明细，全程本地，默认零重依赖。
- analyzer 可插拔：默认 `lexicon` 离线可用，可切 `huggingface` / `llm`。
- 看板与运营看板风格统一，可离线、可演示。

**Non-Goals:**
- 不做公共平台评价爬取与第三方数据买卖（合规风险）。
- 不接需企业资质的开放平台 API。
- v1 不做多用户 / 权限 / 持久化数据库（内存会话 + 演示数据足够）。

## Decisions

**D1. 数据入口 = 商家后台导出（Excel/CSV）+ 粘贴文本**
- 用户从自己店铺后台导出评价（拼多多 / 千牛均支持），上传或粘贴；粘贴支持每行一条、可选 `[星级]` 前缀。
- 进阶（v1.5，可选）：RPA 半自动导出——复用上架助手的 Playwright 能力，用户已登录自己店铺后台，脚本代点导出；仍只采集用户自有数据。
- 理由：零反爬/合规风险，演示闭环最短。备选「爬公共评价页」被否（法律风险 + 反爬成本）。

**D2. analyzer 可插拔接口**
- 契约：`analyze(text) -> ReviewResult`，字段 `sentiment`（positive | negative | neutral）、`score`（0-1）、`confidence`、`labels?`（维度标签列表）。
- 实现 1 `lexicon`（默认）：jieba 分词 + 内置电商情感词典打分 + 否定词/程度副词规则；离线、毫秒级。
- 实现 2 `huggingface`：`uer/roberta-base-finetuned-jd-binary-chinese`（torch + transformers），首次下载模型后离线。
- 实现 3 `llm`：OpenAI 兼容 chat completions，返回情感 + 维度标签（物流/质量/描述/售后/价格/其他），复用 `src/config.py` 的 key 读取模式。
- 选择：`ANALYZER` 环境变量（默认 `lexicon`），与现有 `CHANNEL` 约定一致；`llm` 失败自动回退 `lexicon`。
- 备选：只做 lexicon——被否，京东 RoBERTa 免费且更准，可插拔成本低。

**D3. 痛点挖掘 = 好评/差评对比**
- jieba 分词 + 自定义停用词（含电商词）→ 按 sentiment 分组 → TF-IDF 统计差评相对好评的高权重词 → 痛点词 TopN + 随机抽样 3 条例句。
- 维度标签（v1.5，llm 模式）：物流 / 质量 / 描述 / 售后 / 价格 / 其他。

**D4. 后端与前端形态**
- 后端：`reviews/backend/` FastAPI（端口 8503），复用 `webapp/` 的模式（内存会话 + 同步分析，单用户演示级）。
- 前端：FastAPI 托管静态页（HTML + Tailwind + ECharts），与 `dashboard/` 风格一致；不新增 npm 工程。
- 理由：分析结果以图表/表格为主、无复杂交互；静态页可离线、构建链最简。
- 备选：React（与 `frontend/` 统一）——v2 若交互复杂化再迁移。

**D5. 合规与提示**
- 界面明示「数据仅在本机分析，不上传」；导入时提示用户使用自己店铺后台导出的数据。
- 不使用、不缓存任何第三方抓取数据；示例数据为内置演示用模拟评价。

## Architecture

```
用户评价数据（商家后台导出 Excel/CSV 或粘贴文本）
        │ 上传
        ▼
reviews/backend（FastAPI :8503）
  ├─ review_import.py    列映射 / 清洗 / 去重
  ├─ analyzer/           lexicon | huggingface | llm（可插拔）
  ├─ pain_points.py      TF-IDF 对比 + 例句抽样
  └─ /api/…              分析结果 JSON（内存会话）
        │
        ▼
reviews/frontend（后端托管静态页）
  情感分布 · 差评率趋势 · 平台/商品对比 · 痛点词云 · 差评明细
```
