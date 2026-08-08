## 1. 数据导入与标准化（review-import）

- [x] 1.1 `reviews/backend/review_import.py`：Excel/CSV 解析（`pandas`），列别名映射（评价内容 / 星级 / 日期 / 商品 / 平台 / 店铺等，支持中英文列名）
- [x] 1.2 清洗：空内容过滤（含 NaN 安全处理）、去重（内容+日期+商品）、星级归一（数字 / 星号串 / emoji / 文本）
- [x] 1.3 粘贴文本解析：每行一条评价，可选 `[N星]` 前缀与分隔符
- [x] 1.4 内置演示数据生成器：`reviews/backend/demo_data.py`（多平台样例评价，好评/中评/差评混合）

## 2. 情感分析 analyzer（sentiment-analysis）

- [x] 2.1 analyzer 接口与工厂：`reviews/backend/analyzer/`，`ANALYZER` 环境变量（默认 `lexicon`），`analyze(text) -> ReviewResult`
- [x] 2.2 `lexicon` 实现：jieba 分词 + 电商情感词典（正/负向各百余词）+ 否定词/程度副词规则，离线可用
- [ ] 2.3 `huggingface` 实现：`uer/roberta-base-finetuned-jd-binary-chinese`（可选依赖，惰性加载）
- [ ] 2.4 `llm` 实现：OpenAI 兼容 chat completions，返回情感 + 维度标签；失败自动回退 `lexicon`

## 3. 痛点挖掘（pain-point-mining）

- [x] 3.1 分词 + 电商停用词表（`reviews/backend/pain_points.py`）
- [x] 3.2 好评/差评分组 TF-IDF 对比，产出差评相对高权重词（纯 Python，无 sklearn 依赖）
- [x] 3.3 痛点词 TopN + 随机抽样例句（每条痛点词配最多 3 条差评例句）

## 4. FastAPI 后端（可选增强，v1.5+ 接入高级 analyzer 时启用）

- [ ] 4.1 项目骨架：`reviews/backend/`，端口 8503，静态托管 `reviews/frontend/`
- [ ] 4.2 API：`POST /api/session`、`POST /api/import`（文件/文本）、`POST /api/analyze`、`GET /api/summary`、`GET /api/pain-points`、`GET /api/reviews`
- [ ] 4.3 配置：`src/config.py` 新增 `ANALYZER` / `REVIEW_LLM_KEY` / `REVIEW_LLM_BASE` / `REVIEW_LLM_MODEL`

## 5. 前端看板（review-dashboard，v1 已纯前端落地）

- [x] 5.1 静态页骨架：**科技蓝/白浅色 SaaS 风格**（primary `#2563EB` / 柔和红 `#F43F5E` / 柔和绿 `#10B981`），卡片式，响应式
- [x] 5.2 顶部筛选栏：开始/结束日期、平台、店铺、品类、商品编码 + 重置 + 数据摘要
- [x] 5.3 商品评价总览：8 指标卡（评价/正面/负面/观点/正面观点/负面观点/观点正面率/观点负面率），环比「绿降红升」
- [x] 5.4 情感结构与趋势：观点正负占比、评价正负占比环形 + 多维度趋势折线
- [x] 5.5 观点声量洞察：观点标签排名（负面/正面/整体切换 + 进度条）、观点词云（情感染色）、负面观点趋势（柱 + 线组合）
- [x] 5.6 观点词频概况：属性情感对比堆叠条形（肤感/气味/使用感/价格…）+ 观点词频明细表
- [x] 5.7 商品声量洞察：负面/正面声量商品排名（含情感结构迷你条）
- [x] 5.8 数据入口：上传 Excel（SheetJS 浏览器解析，中英文列名映射）+ 载入模拟数据

## 6. 测试

- [x] 6.1 单元检查：`scripts/reviews_unit_check.py`（导入映射 / 星级归一 / lexicon / TF-IDF 痛点，全部通过）
- [x] 6.2 冒烟测试：`scripts/reviews_smoke.py`（Playwright，1440px / 375px，8 KPI / 6 图表 / 表格 / 无横向滚动 / 0 控制台错误）
