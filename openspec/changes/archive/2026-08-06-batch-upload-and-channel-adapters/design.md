## Context

现状（见 proposal.md - Why）：`app.py` 单图上传 + 单条审核 + `src/rpa.py` 直连本地模拟后台；`src/rpa.py` 已具备重试、回读校验、截图等可复用能力。项目非 git 仓库，测试脚本（`scripts/smoke_test.py` / `ui_test.py` / `unit_checks.py`）依赖 `listing_payload_for_rpa()` 这一 payload 契约。现有 `openspec/specs/vision-recognition/spec.md` 为单图识别契约，本次不修改。

## Goals / Non-Goals

**Goals:**
- 多图上传 → 逐图生成 → 批量审核（可编辑、可勾选）→ 批量顺序发布，单条失败隔离
- 用渠道适配器契约隔离平台差异，Mock 后台作为首个实现，API / RPA 预留骨架
- 演示闭环：模拟后台支持下架，支撑 `publish_off` 契约

**Non-Goals:**
- 不接入任何真实平台（淘宝 / 京东 / 抖店 / 闲鱼）；`ApiChannel` / `RpaChannel` 只留骨架与接入文档
- 不引入数据库 / 消息队列；批量任务状态存于 `session_state`（演示级）
- 不做并发发布；批量发布刻意串行，避免登录态竞争与平台限流

## Decisions

**D1. 渠道适配器包 `src/channels/`**
- `base.py`：`BaseChannel`（ABC）契约：`name` / `check_ready() -> (ok, message)` / `publish(item) -> ChannelResult` / `publish_off(item) -> ChannelResult`；`ChannelResult` 复用现有结构化结果形态（success / steps / message / screenshot / submitted_at）。
- `rpa_channel.py`：`RpaChannel(BaseChannel)` 抽象出浏览器启动、`_retry`、回读校验、截图等公共能力（从 `src/rpa.py` 迁移）。
- `mock_channel.py`：`MockChannel(RpaChannel)` 接管现有模拟后台表单流程；`publish_off` 走模拟后台新增的 `POST /delist`。
- `api_channel.py`：`ApiChannel(BaseChannel)` 骨架——`publish` / `publish_off` 抛 `NotImplementedError`，`check_ready` 返回「未实现」，附 docstring 说明未来如何接官方开放平台（拼多多 / 1688 起步）。
- `registry.py`：`get_channel(name)` 工厂，按 `CHANNEL` 环境变量解析（默认 `mock`），未知渠道报错。
- 理由：与调研结论一致（参考 ecom-agent 的 BasePlatformAdapter / pds-tool 的 push 模块）；选 ABC + 注册表而非单文件 if/else，让「新增渠道 = 新增一个模块」的演进路径可讲。
- 备选：把适配器塞进 `rpa.py` 加分支——被否，接口会随平台数量膨胀，且 API 渠道与 RPA 渠道机制完全不同。

**D2. `src/rpa.py` 过渡策略**
- 重构为 `src/channels/` 后，`src/rpa.py` 保留为薄兼容层（re-export `submit_listing` → `MockChannel.publish`），`app.py` 与 `smoke_test.py` 迁移到新契约后删除该文件。
- 理由：项目非 git 仓库，无版本回退；薄兼容层让 UI 与测试可在同一次改动中分批迁移，降低一次性大改风险。

**D3. 批量数据模型（`session_state`）**
- `SS["items"]: list[dict]`，每条：`id`（uuid，兼作幂等键）、`image`（bytes）、`vision`、`listing`、`status`（`pending / publishing / success / failed / skipped`）、`error`、`rpa_result`、`selected`（bool）。
- 批量上限 `BATCH_IMAGE_LIMIT`（默认 20），超过截断并提示；图片字节存内存，避免引入磁盘暂存。
- 理由：演示级足够；真实批量应落库（设计文档中注明未来演进点）。

**D4. 审核交互**
- 顶部 `st.dataframe` 只读概览（缩略图 / 标题 / 类目 / 状态），每条商品一个 `st.expander`：勾选框 + 标题输入 + 类目选择 + 属性编辑 + 「重新生成」按钮（仅该条 seed+1）+ 该条发布状态。
- 备选：`st.data_editor` 单表编辑——属性 dict 与文本互转有丢失风险，且无法放下单行「重新生成」按钮；expander 方案实现更稳、更贴合现有单条审核控件，复用成本低。

**D5. 批量发布循环**
- 新增 `src/batch.py`：`publish_batch(channel, items) -> summary`——按勾选顺序串行发布，每条发布前置 `publishing`、结束写 `success/failed`，单条异常捕获后继续；`app.py` 用 `st.progress` 展示进度，结束后展示逐条结果。
- 幂等：每条 `id` 作为 `idempotency_key` 随 payload 提交；模拟后台 `POST /submit` 校验重复 `idempotency_key` 时返回既有记录（不重复落盘）。
- 理由：失败隔离与幂等是批量铺货的刚需（调研中 snaplist / 速卖通技能均强调），也是面试讲点。

**D6. 模拟后台扩展**
- `POST /submit` 接受 `idempotency_key`（可选字段），重复时返回已有记录。
- 新增 `POST /delist`（`item_id`）+ 记录状态字段 `status: listed / delisted`；`/submissions` 页面显示状态并放下架按钮。
- 理由：最小改动支撑 `publish_off` 契约的演示闭环。

**D7. 配置与文档**
- `src/config.py` 新增 `CHANNEL`、`BATCH_IMAGE_LIMIT`、`SESSION_DIR`（RPA 登录态持久化目录，Mock 暂不使用）。
- README 更新功能特性 / 架构图 / 面试讲解要点（批量 + 适配器 + 幂等）。

## Risks / Trade-offs

- [session_state 存图片字节，大批量占内存] → 设 `BATCH_IMAGE_LIMIT` 上限；真实场景演进为落盘/对象存储。
- [expander 逐条审核在大批量下页面长] → 演示场景 20 条以内可接受；概览表 + 折叠设计缓解。
- [幂等键依赖前端生成 uuid，刷新后变化] → 幂等键在生成 listing 时固定并存入 `SS["items"]`，不随 rerun 改变。
- [RPA 渠道登录态未在本次实现] → 契约与 `SESSION_DIR` 预留，`RpaChannel` 基类实现 `storage_state` 读写；Mock 无需登录。
- [`src/rpa.py` 兼容层短期双入口] → 同一变更内完成迁移后删除，不留长期双实现。

## Migration Plan

1. `src/channels/` 新建 + 从 `rpa.py` 迁移公共能力；`rpa.py` 改为薄兼容层。
2. 模拟后台加 `idempotency_key` 与 `/delist`，更新模板与 `submissions.json` 结构（旧记录兼容读取）。
3. `app.py` 改批量上传 / 审核 / 发布，迁移到 `channels` 契约。
4. `smoke_test.py` / `unit_checks.py` / `ui_test.py` 适配新契约并回归。
5. 删除 `src/rpa.py` 兼容层，更新 README。

## Open Questions

- 无：均可按上述设计推进，且不改变 specs / tasks 分解。