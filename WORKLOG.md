# VisiPublish 工作管理日志

> 记录时间：2026-08-07（关机前检查点）。用于跨会话恢复进度。

## 1. 项目全景

| 应用 | 位置 | 状态 | 入口 |
|---|---|---|---|
| 全平台电商运营看板 | `dashboard/` | ✅ 完成（暗色大屏，Excel 导入 + 筛选联动 + 7 图表） | 双击 `dashboard/index.html` |
| 项目展示站 | `site/` | ✅ 完成（浅色卡片，3 项目卡；其中「评价分析」仍是「规划中」占位） | 双击 `site/index.html` |
| 商品评价分析·声量洞察看板 | `reviews/frontend/` + `reviews/backend/` | ✅ 前端 v1 完成；后端核心完成（可选增强） | 双击 `reviews/frontend/index.html` |
| 电商 AI 智能上架助手（React+FastAPI） | `frontend/` + `webapp/` | ✅（他人/此前会话完成） | `webapp` |

## 2. 测试状态（关机前最后全绿）

- `scripts/dashboard_smoke.py` ✅ 8 KPI / 7 图表 / 导入 / 联动 / 0 控制台错误
- `scripts/site_smoke.py` ✅ 1440px + 375px / 无横向滚动 / 0 错误
- `scripts/reviews_unit_check.py` ✅ 17 项（导入映射 / 星级归一 / lexicon / TF-IDF 痛点）
- `scripts/reviews_smoke.py` ✅ 8 KPI / 6 图表（含词云）/ 表格 / 标签切换 / 0 错误
- 依赖：`.venv` 已有 `jieba 0.42.1`、`openpyxl 3.1.5`、`pandas`、`fastapi`、`uvicorn`

## 3. Git 状态（重要：有未提交内容）

- 未提交：`README.md`、`openspec/changes/2026-08-07-review-insights/design.md`、`.../tasks.md`、`reviews/frontend/`（含 `libs/`，未确认是否入库）、`scripts/reviews_smoke.py`
- 已提交（此前会话）：`dashboard/`、`site/`、`reviews/backend/`、`scripts/` 其余测试、OpenSpec change 主体
- 分支 `main`，远端 `origin/main`

## 4. 待办（按优先级）

1. ~~展示站收尾~~ ✅（2026-08-08）：评价分析卡改「已完成」+ 截图 `site/assets/reviews-dashboard.png` + 链接 + 页脚入口；hero 状态条三项目全「运行中」。
2. ~~reviews 前端补「粘贴文本」导入~~ ✅：头部按钮 + 弹窗（`[N星]` 前缀、按行解析、去重、隐私提示），冒烟测试覆盖。
3. **双轴代码审查** ✅（2026-08-08，就地执行）：见本文件第 6 节报告；P2 缺陷已修复（日期列映射、后端 .xls 容错），spec 已与 v1 对齐。
4. **FastAPI 后端（可选 v1.5）**：spec 4.x；接 `huggingface` / `llm` analyzer 时启用。
5. **提交策略**：确认 vendored `libs/`（约 2.5MB）是否入库；确认后 `git add` + commit。

## 6. 代码审查报告（2026-08-08，双轴就地执行）

> 说明：本会话无子 agent 工具（MCP 资源为空），未按 `code-review` 技能的并行子代理方式执行，改为按同方法论就地做双轴审查（Standards / Spec 各自独立过一遍）。

### Standards 轴
- `[P2]` 已修复：reviews 前端 `onFileChange` 用原始键 `r.date || r['日期']` 取日期，`评价时间/评论时间/time` 等别名表头会被当无效行跳过 → 改用 `normalizeRow` 已映射的 `row.date`。
- `[P2]` 已修复：后端 `import_excel` 声明支持 `.xls` 但 `engine="openpyxl"` 读不了 `.xls` → 增加 xlrd 回退 + 明确报错。
- `[P3]` 已清理：前端 `renderTagAndTables()` 空方法 + `tagMode` watch 死代码 → 删除。
- `[P3]` 判断性（保留）：情感词典/列别名/星级归一在 `reviews/backend`（Python）与 `reviews/frontend`（JS）双份存在 —— v1「纯前端可双击 + 后端可选」架构下的刻意接缝，接入高级 analyzer 时再收敛为共享数据。
- 无 P0/P1；命名与结构整体清晰，中文注释与项目惯例一致。

### Spec 轴
- `[P2]` 已修复：`sentiment-analysis` spec 原要求 huggingface/llm 的 SHALL 回退行为，v1 未实现（design 已明确 v1.5）→ spec 修订为「lexicon SHALL，huggingface/llm 为未来可选」，避免过度承诺。
- `[P3]` 已补：review-dashboard spec 要求导入区提示「使用自己店铺后台导出的数据」→ 粘贴弹窗已加提示行。
- 其余：review-import（列映射/星级归一/清洗去重/粘贴文本）、pain-point-mining（TF-IDF+例句）、review-dashboard（6 大模块 + 筛选 + 隐私提示）与实现一致。

## 5. 待用户确认的事项（放最后，等用户回来）

- ① 是否把 `reviews/frontend/libs/` 等 vendored 依赖提交进 git（还是加 `.gitignore` 走 CDN 回退）。
- ② 展示站「评价分析」卡的文案与链接是否按建议更新。
- ③ 粘贴文本导入入口是否要加（建议加，符合 spec）。
- ④ FastAPI 后端现在推进，还是等接入高级 analyzer 时再推进。
- ⑤ 代码审查用子 agent 执行（需要具备多 agent 工具的会话环境）。

## 7. 提交记录（2026-08-08）

- 用户确认「按建议来」→ 执行本地提交（含 vendored `libs/`，与 dashboard/libs 已入库的 120 个文件保持一致）。
- 提交前修复：`scripts/dashboard_smoke.py` 的 `networkidle` 改为 `domcontentloaded`——dashboard 页面有 116 个本地字体文件（约 4.6MB），`networkidle` 永不安静导致冒烟超时；页面本身无缺陷。
- 提交前验证全绿：dashboard / site / reviews 冒烟 + reviews 单元检查 + openspec validate。
- 备注（残余风险，P3）：Noto Sans SC 字体按 unicode-range 拆成 116 个 woff2，首屏请求较多；如需优化可改为仅引所需字重或系统字体回退。
