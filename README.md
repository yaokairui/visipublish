# VisiPublish · 电商 AI 工具集（个人项目展示）

本地优先的电商自动化工具集，目前包含三个内容模块：

- **AI 上架助手**（主力模块）：React + FastAPI 全栈 —— 批量商品图识别、AI 标题生成、人工审核队列、Playwright RPA 批量上架。代码见 `frontend/`、`webapp/`、`src/`、`mock_backend/`。
- **全平台电商运营看板**：纯前端销售看板 —— Excel 导入、五重筛选联动、8 项核心指标、7 组 ECharts 图表。代码见 `dashboard/`。
- **电商评价分析**（进行中）：评论数据导入、痛点词库与归因分析的后端库。代码见 `reviews/backend/`。

另有 `site/` 个人作品集展示站。README 中提到的调研报告与业务数据均为**模拟演示数据**，不涉及任何真实业务。

## 1. 项目简介

一个「React 前端 + FastAPI 后端 + Vision API 多模态识别 + 运营规则库 + 渠道适配器 + Playwright RPA 自动上架」的电商 AI 智能上架面试演示项目：用户**批量上传商品图片**，系统逐张识别商品信息，按运营规则与 **AI 大模型**生成标题（含电商曝光关键词），在**批量审核队列**人工确认后，由**渠道适配器**（默认本地模拟后台，Playwright RPA 填表）批量上架；支持幂等防重复、失败隔离与一键下架。

> 原 Streamlit 界面（`app.py`）已弃用，保留作为参考实现；新前端为 `frontend/`（React + Vite + Tailwind），后端为 `webapp/`（FastAPI）。

## 2. 功能特性

- **现代 Web 前端**：React + Tailwind，AI-Native 暗色运维风设计系统（Fira Sans / Fira Code、Lucide 图标、语义色令牌、Toast / 骨架屏 / 进度条、无 emoji 图标、支持 reduced-motion）。
- **批量上传**：拖拽 / 多选上传（默认单批上限 20 张），缩略图预览，逐张独立识别与生成，单张失败不中断整批。
- **AI 识别结构化 JSON**：配置 `VISION_API_KEY` 后调用 OpenAI 兼容的 Vision API，返回 `{category, color, material, style}`。
- **运营规则库生成**：内置 5 个类目规则（T恤 / 连衣裙 / 牛仔裤 / 卫衣 / 运动鞋），标题按「季节 + 品牌 + 商品名 + 核心卖点」模板拼装。
- **AI 生成标题（含曝光关键词）**：每条商品额外调用大模型按「图片 + 识别信息 + 类目曝光关键词池」生成 3 条标题候选（如 `2026新款红色纯棉T恤男夏季透气简约ins风百搭短袖`），规避绝对化用语与违禁词。
- **标题来源可选**：审核时每条可切换「AI 标题 1/2/3 / 规则模板 / 手动输入」，符合真实业务中「标题由商家主导」的诉求；未配置 API Key 时自动回退规则模板。
- **批量审核队列**：概览表格 + 可展开行编辑（标题来源 / 标题 / 类目 / 属性 / 提示词）、单条「重新生成」、识别原始 JSON、占位图与 RPA 日志。
- **批量发布**：按勾选顺序串行上架（FastAPI 后台线程任务 + 前端 1s 轮询进度），单条失败隔离 + 幂等（`idempotency_key` 防重复上架）。
- **渠道适配器**：`src/channels/` 统一契约（登录 / 上架 / 下架 / 状态检查）；`MockChannel`（Playwright RPA）已实现，`ApiChannel`（拼多多 / 1688 等官方 API）预留骨架。
- **RPA 健壮性**：提交前探活、关键步骤自动重试（3 次 / 间隔 1.5s）、填写后回读校验、成功/失败均截图。
- **一键下架**：成功上架后可在审核区对单条下架（模拟后台记录状态 → `delisted`）。
- **离线 Mock 回退**：`VISION_API_KEY` 留空或真实 API 失败时，自动改用 Pillow 像素主色分析 Mock 识别，离线即可跑通全流程。
- **本地模拟电商后台**：Flask 提供上架表单（含幂等键）、成功页、已上架记录页（支持下架）与健康检查。

## 3. 系统架构

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌──────────────────┐
│  React 前端      │   │  FastAPI 后端    │   │  运营规则库 / AI  │   │  渠道适配器        │
│  frontend/ (Vite)│──▶│  webapp/ :8502  │──▶│  src/rules.py   │──▶│  MockChannel(RPA) │──▶ 模拟后台 :8010
│  上传/审核/上架   │   │  会话/任务/轮询   │   │  title_ai.py    │   │  ApiChannel(骨架)  │
└─────────────────┘   └─────────────────┘   └─────────────────┘   └──────────────────┘
        ▲                     │  Vision API / Mock（Pillow 主色）
        └───── 批量审核（可编辑 / 勾选 / 单条重新生成）─────┘
```

- **前端**：`frontend/`（React + TS + Tailwind，构建产物 `frontend/dist/` 由 FastAPI 静态托管）；dev 模式 `npm run dev`（5173，`/api` 代理到 8502）。
- **后端**：`webapp/main.py`（FastAPI）提供会话 / 生成 / 审核 / 发布任务 API，契约见 `docs/web_api_contract.md`；复用 `src/` 全部业务逻辑。
- **识别层**：`src/vision_client.py` 统一入口 `analyze_image()`——配置 `VISION_API_KEY` 走真实 API；未配置或失败自动回退 Mock（Pillow 主色分析）。
- **规则层**：`src/rules.py` 内置 `CATEGORY_RULES`——标题模板、卖点池、属性白名单、提示词模板、类目曝光关键词池（`exposure_keywords`）。
- **标题 AI**：`src/title_ai.py` 按「图片 + 识别信息 + 关键词池」生成标题候选；`resolve_title()` 把「标题来源」统一解析为最终标题。
- **渠道层**：`src/channels/` 统一契约（`check_ready` / `publish` / `publish_off`）；`MockChannel` 用 Playwright 填表，带重试、回读校验、截图。
- **批量层**：`src/batch.py` 串行发布 + 单条异常隔离 + `idempotency_key` 幂等；后端以线程任务运行，前端轮询进度。
- **模拟后台**：`mock_backend/server.py`（Flask）提供上架表单、幂等去重、`/delist` 下架与记录落盘（`submissions.json`）。

## 4. 目录结构

```
VisiPublish_Agent/
├── frontend/                  # React + Vite + Tailwind 前端（新）
│   ├── src/App.tsx            # 应用主逻辑：会话/生成/审核/发布/轮询
│   ├── src/components/        # Sidebar / UploadZone / ReviewTable / ItemRow / PublishPanel / Toast ...
│   ├── src/api.ts             # API 封装（X-Session-Id 会话头）
│   └── dist/                  # 构建产物（FastAPI 托管）
├── webapp/main.py             # FastAPI 后端（新）：会话/生成/审核/发布任务/静态托管
├── src/                       # 业务逻辑（前后端共用）
│   ├── vision_client.py       # 视觉识别：真实 API + Mock 回退
│   ├── rules.py               # 运营规则库 + 属性白名单 + 曝光关键词池 + ATTR_LABELS
│   ├── listing_generator.py   # 组装 listing
│   ├── title_ai.py            # AI 标题生成 + 标题来源解析
│   ├── placeholder.py         # Pillow 占位图
│   ├── batch.py               # 批量发布：串行 + 失败隔离 + 幂等
│   └── channels/              # 渠道适配器：base / rpa_channel / mock_channel / api_channel / registry
├── mock_backend/              # 本地模拟电商后台（Flask，RPA 操作目标）
├── scripts/
│   ├── start_project.py       # 一键启动 / 停止（mock 后台 + FastAPI）
│   ├── unit_checks.py         # 单元回归检查
│   ├── smoke_test.py          # RPA 上架 + 幂等 + 下架冒烟
│   ├── ui_test.py             # React 前端全流程 UI 测试
│   └── verify_vision_api.py   # 真实 API 识别 + AI 标题实测
├── docs/web_api_contract.md   # 前后端 API 契约
└── output/                    # 占位图 / RPA 截图 / 日志
```

## 5. 快速开始（Windows，PowerShell）

```powershell
# 1. 创建并激活虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 2. 安装 Python 依赖（含 fastapi / uvicorn）
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器内核
playwright install chromium

# 4. 构建前端
cd frontend
npm install
npm run build
cd ..
```

> 可选：`Copy-Item .env.example .env` 生成配置文件（不复制也能以 Mock 模式离线运行）。

```powershell
# 一键启动：模拟后台（8010）+ Web 前端（8502）
.venv\Scripts\python scripts\start_project.py
# 浏览器访问 http://127.0.0.1:8502
```

前端开发模式（改 UI 热更新）：

```powershell
cd frontend
npm run dev        # http://localhost:5173，/api 代理到 8502
```

## 6. 配置说明

将 `.env.example` 复制为 `.env` 后按需修改。所有变量由 `src/config.py` 通过 `os.getenv()` 读取：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VISION_API_KEY` | （空） | 留空 = 使用内置 Mock 识别（离线可演示）；填入后走真实 Vision API |
| `VISION_API_BASE` | `https://api.openai.com/v1/chat/completions` | OpenAI 兼容 Chat Completions 端点，可换成 agnes 等兼容网关 |
| `VISION_MODEL` | `gpt-4o-mini` | 多模态模型名称 |
| `CHANNEL` | `mock` | 发布渠道：`mock`（本地模拟后台）；`api` 为官方开放平台 API 骨架（未实现） |
| `BATCH_IMAGE_LIMIT` | `20` | 单批上传图片上限 |
| `AI_TITLE_COUNT` | `3` | 每张图片生成的 AI 标题候选数量 |
| `TITLE_MAX_LEN` | `60` | AI 标题最大字符数（按目标平台调整） |
| `WEB_HOST` / `WEB_PORT` | `127.0.0.1` / `8502` | FastAPI Web 服务监听地址 / 端口 |
| `MOCK_BACKEND_HOST` / `MOCK_BACKEND_PORT` | `127.0.0.1` / `8010` | 模拟后台监听地址 / 端口 |
| `RPA_HEADLESS` | `true` | `true` = 无头模式；`false` = 弹出可见浏览器（面试演示更直观） |
| `RPA_BROWSER` | `chromium` | Playwright 使用的浏览器 |

## 7. 演示流程（面试现场脚本）

1. **批量上传**：拖拽或多选多张商品图，缩略图预览；超过单批上限自动截断提示。
2. **点击【开始生成】**：逐张调用识别 API + AI 标题生成（各 3 条候选），单张失败自动跳过并标注。
3. **批量审核**：概览表格 + 展开行编辑；标题可切换「AI 标题 / 规则模板 / 手动输入」，可编辑类目 / 属性 / 提示词，单条「重新生成」只轮换本条卖点。
4. **勾选与上架**：生成后默认全选可上架条目；点击【确认无误，批量上架】，前端轮询任务进度，展示逐条成功 / 失败结果。
5. **查看上架成果**：打开 `http://127.0.0.1:8010/submissions` 查看已上架记录（含状态，可下架）。
6. **演示下架**：审核区对已上架条目点【下架】，模拟后台记录状态变为「已下架」。
7. **演示幂等**：同一批重复上架不会产生重复记录（`idempotency_key` 去重）。

> 面试话术：强调「AI 不直接上架，必须经过人工审核」；批量上架做了失败隔离与幂等；前端采用 React + FastAPI 真实全栈架构，前端只负责交互，业务逻辑全部在后端 `src/` 复用。

## 8. 面试讲解要点

- **全栈分层**：React（交互）→ FastAPI（API / 会话 / 任务）→ `src/`（识别 / 规则 / 标题 AI / 渠道 / 批量）→ 模拟后台；契约文档 `docs/web_api_contract.md` 前后端对齐。
- **运营规则库可配置化**：`src/rules.py` 的 `CATEGORY_RULES` 把标题模板、卖点池、属性白名单、提示词模板、曝光关键词全部沉淀为数据结构，新增类目只需加一条规则。
- **属性白名单归一化**：`resolve_attributes()` 将 AI 返回值与白名单枚举归一化匹配，非法值回退默认，避免脏数据上架。
- **AI 标题生成（业务视角）**：真实业务标题由商家主导，因此标题提供三种来源（AI 生成含曝光关键词 / 规则模板 / 手动输入）；`resolve_title()` 统一解析，AI 不可用时自动回退规则模板。
- **批量与失败隔离 + 幂等**：`src/batch.py` 串行发布、单条异常隔离；固定 `id` 作为 `idempotency_key` 防重复上架；后端线程任务 + 前端轮询是实现异步进度的方式。
- **渠道适配器**：`BaseChannel` 统一契约，`MockChannel` / `ApiChannel` 是两种策略；未来接拼多多 / 1688 官方 API 或闲鱼式 RPA，只需新增 Channel 模块并注册。
- **RPA 健壮性**：提交前 `/health` 探活；关键步骤重试 3 次 / 间隔 1.5s；`input_value()` 回读校验防「填错位置」；成功/失败截图到 `output/screenshots/`。
- **Mock 回退**：`analyze_image()` 优先真实 API，异常回退 Mock（Pillow 64×64 缩放 + 中位切分量化 + 11 色阈值判定主色），离线可跑通且颜色来自真实像素。

## 9. 常见问题（FAQ）

- **提示「未安装 Playwright 浏览器内核 / Executable doesn't exist」**：在虚拟环境执行 `playwright install chromium`。
- **端口被占用**：改 `.env` 的 `MOCK_BACKEND_PORT` / `WEB_PORT` 后重启；如修改过 `MOCK_BACKEND_URL` 需同步。
- **前端修改后不生效**：`cd frontend && npm run build` 重新构建；开发期用 `npm run dev` 热更新。
- **没有 API Key**：自动使用 Mock 识别，AI 标题自动回退规则模板；识别来源在条目上有徽标展示。
- **如何接入真实电商平台**：官方发布 API 均需企业资质 + 应用审核；门槛最低是拼多多（`pdd.goods.add`）与 1688（`alibaba.product.add`）。实现 `src/channels/api_channel.py` 的 `publish` / `publish_off` 并在 `registry.py` 注册后设置 `CHANNEL=api` 即可，前端无需改动。详见 `api_channel.py` docstring 与 `电商批量上架调研报告.md`。
- **RPA 失败如何排查**：① 确认模拟后台 `/health` 返回 `{"ok": true}`；② 前端条目「RPA 执行日志」看步骤；③ 查看 `output/screenshots/rpa_*.png` 截图；④ 若改过模板，确保 `src/channels/mock_channel.py` 的 `SELECTORS` 与 `index.html` id 一致。
- **想回到旧 Streamlit 界面**：`app.py` 保留为参考实现，可用 `streamlit run app.py` 启动（端口 8501）。

## 10. 技术栈清单

- **前端**：React 19 + TypeScript + Vite + Tailwind CSS v4 + lucide-react
- **后端**：FastAPI + uvicorn + python-multipart（`webapp/`）
- **多模态识别**：OpenAI 兼容 Vision API（`requests` 直连，`response_format` 强制 JSON）
- **浏览器自动化**：Playwright（Python）+ Chromium
- **图像处理**：Pillow（占位图 + Mock 主色分析）
- **模拟后台**：Flask + Jinja2（`mock_backend/`）
- **配置管理**：python-dotenv（`.env`）
- **数据存储**：本地 JSON（`mock_backend/submissions.json`）+ 内存会话（`webapp`）

## 11. 全平台电商运营看板（纯前端 · dashboard/）

- 入口：双击 `dashboard/index.html` 即可离线运行（依赖库已内置在 `dashboard/libs/`，缺失时自动回退 CDN）。
- 功能：上传 Excel（SheetJS 本地解析，自动识别中文/英文列名）/ 恢复内置示例数据（6 平台 × 12 店铺 × 61 天）/ 日期·平台·店铺·品类·新老客五重筛选实时联动 / 8 项核心指标（含环比）/ 7 组 ECharts 图表 / 店铺健康预警表 / 商品销售 TOP20。
- 数据仅保存在浏览器内存，刷新即清空，不会上传任何服务器。
- 冒烟测试：`.venv/Scripts/python.exe scripts/dashboard_smoke.py`。

## 12. 项目展示站（纯静态 · site/）

- 入口：双击 `site/index.html` 即可离线打开（依赖库在 `site/libs/`，缺失时回退 CDN）。
- 内容：个人作品集首页 —— Hero + 项目网格（运营看板 / 上架助手 / 评价分析-规划中）+ 理念 + 页脚，含各项目截图与入口链接。
- 设计：深空蓝底 + 运行绿（ui-ux-pro-max 设计系统），Inter 字族，滚动入场动画，尊重 `prefers-reduced-motion`。
- 冒烟测试：`.venv/Scripts/python.exe scripts/site_smoke.py`（1440px / 375px 双端）。

## 13. 商品评价分析·声量洞察看板（reviews/）

- 入口：双击 `reviews/frontend/index.html` 即可离线运行（依赖库在 `reviews/frontend/libs/`，缺失时回退 CDN）。
- 功能：上传商家后台导出的评价 Excel（SheetJS 浏览器解析）或载入模拟数据 → 观点提取（属性×情感）→ 8 项指标卡（含环比「绿降红升」）/ 情感结构双环形 + 多维度趋势 / 观点标签排名（正负/整体切换）/ 观点词云（情感染色）/ 负面观点趋势（柱+线）/ 属性情感对比 / 观点词频表 / 商品声量正负排名。
- 风格：科技蓝/白浅色 SaaS 卡片式，柔和红绿情感色；数据仅在本机分析，不上传。
- Python 后端核心（可选增强）：`reviews/backend/` 已含 lexicon 情感分析、导入标准化、痛点挖掘（TF-IDF）；`ANALYZER` 环境变量可切换分析实现。
- 单元检查：`.venv/Scripts/python.exe scripts/reviews_unit_check.py`；冒烟测试：`.venv/Scripts/python.exe scripts/reviews_smoke.py`。
