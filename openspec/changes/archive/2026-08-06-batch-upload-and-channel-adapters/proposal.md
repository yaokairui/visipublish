## Why

当前 MVP 仅支持「单图上传 + 单一写死的模拟后台 RPA」，无法展示批量商品管理与多渠道可插拔能力。真实平台（淘宝/京东/抖店等）的商品发布 API 均需企业资质与应用审核，现阶段不应直接接入；因此先把「批量处理」与「渠道适配器」两块抽象做出来，既补全演示完整度，也为未来接入官方 API / 第三方 ERP / 闲鱼式 RPA 铺好接缝。

## What Changes

- **批量上传与生成**：上传区改为多图上传（`accept_multiple_files=True`），每张图片独立走识别 → 规则生成，`session_state` 维护 `listings` 列表，单张图片失败不中断整批。
- **批量审核队列**：用 `st.data_editor` 展示全部生成结果，可逐条编辑标题 / 类目 / 属性，勾选待上架项；「重新生成」改为对单条轮换卖点。
- **批量发布**：按勾选顺序执行发布，带进度条与单条失败隔离（一条失败不中断整批），复用现有重试 / 回读校验 / 截图机制。
- **渠道适配器**：新增 `src/channels/` 包，定义 `BaseChannel` 契约（`login` / `publish` / `publish_off` / `check_status`）；`MockChannel` 接管现有模拟后台；`ApiChannel`（官方 API）与 `RpaChannel`（浏览器自动化）预留实现骨架与接入文档。
- **模拟后台下架能力**：已上架记录页支持下架操作，以支撑 `publish_off` 契约的可演示闭环。
- **BREAKING**：`src/rpa.py` 的 `submit_listing()` 重构为 `MockChannel` 实现，调用方（`app.py`、`scripts/smoke_test.py`）迁移到新契约。

## Capabilities

### New Capabilities
- `batch-listing`: 多图上传、逐图识别生成、批量审核编辑与勾选、批量顺序发布与失败隔离。
- `channel-adapters`: 可插拔渠道发布契约（登录 / 上架 / 下架 / 状态检查），Mock / API / RPA 三类实现策略与登录态管理约定。

### Modified Capabilities
<!-- 无：vision-recognition 的单图识别契约不变，批量仅在编排层复用 analyze_image() -->

## Impact

- 代码：`app.py`（上传 / 审核 / 发布区重构）、`src/rpa.py`（重构为 channels 实现）、新增 `src/channels/` 包、`src/config.py`（新增 `CHANNEL` 等配置）、`mock_backend/server.py`（下架接口）。
- 测试脚本：`scripts/smoke_test.py`、`scripts/ui_test.py`、`scripts/unit_checks.py` 适配新契约。
- 依赖：不新增第三方依赖（仍为 Streamlit / Playwright / Pillow / Flask）。
- 文档：README 功能特性与面试讲解要点更新。