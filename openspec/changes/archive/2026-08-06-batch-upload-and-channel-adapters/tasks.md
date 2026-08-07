## 1. 渠道适配器层（src/channels/）

- [x] 1.1 新建 `src/channels/` 包：`base.py`（`BaseChannel` ABC：`name` / `check_ready` / `publish` / `publish_off`，`ChannelResult` 结构化结果）+ `__init__.py`
- [x] 1.2 新建 `rpa_channel.py`：`RpaChannel(BaseChannel)` 迁移 `src/rpa.py` 的浏览器启动、`_retry`、回读校验、截图、SELECTORS 约定等公共能力
- [x] 1.3 新建 `mock_channel.py`：`MockChannel(RpaChannel)` 接管模拟后台表单发布；`publish_off` 调用模拟后台 `POST /delist`
- [x] 1.4 新建 `api_channel.py`：`ApiChannel(BaseChannel)` 骨架，`publish` / `publish_off` 抛 `NotImplementedError`，docstring 说明未来接拼多多 / 1688 等官方开放平台的接入方式
- [x] 1.5 新建 `registry.py`：`get_channel(name)` 工厂（默认 `mock`）；`src/config.py` 新增 `CHANNEL`、`BATCH_IMAGE_LIMIT`（默认 20）、`SESSION_DIR`
- [x] 1.6 `src/rpa.py` 改为薄兼容层（re-export `submit_listing` → `MockChannel.publish`），供后续迁移期使用

## 2. 模拟后台扩展

- [x] 2.1 `mock_backend/server.py`：`POST /submit` 支持 `idempotency_key`，重复键返回既有记录不重复落盘
- [x] 2.2 新增 `POST /delist`（按 `item_id` 将记录状态置为 `delisted`）；记录新增 `status` 字段（`listed` / `delisted`），旧记录读取兼容
- [x] 2.3 `submissions.html` 展示记录状态并放下架按钮；`success.html` / 表单模板适配幂等键回显

## 3. 批量前端（app.py）

- [x] 3.1 上传区改为多图：`st.file_uploader(accept_multiple_files=True)`，超过 `BATCH_IMAGE_LIMIT` 截断并提示
- [x] 3.2 「开始生成」循环逐图 `analyze_image()` + `generate_listing()`，单张失败标记 `skipped` 不中断整批，写入 `SS["items"]`
- [x] 3.3 批量审核区：顶部 `st.dataframe` 概览（缩略图 / 标题 / 类目 / 状态）+ 每条 `st.expander`（勾选上架 / 标题 / 类目 / 属性编辑 / 单条「重新生成」/ 该条发布状态）
- [x] 3.4 批量发布区：`【确认无误，批量上架】` 按钮 + `st.progress` 进度 + 逐条成功 / 失败汇总
- [x] 3.5 侧边栏 / 清除会话逻辑适配 `items`，展示当前渠道（`CHANNEL`）与批量信息

## 4. 批量发布逻辑（src/batch.py）

- [x] 4.1 实现 `publish_batch(channel, items)`：按勾选顺序串行发布，状态机 `publishing → success / failed`，单条异常捕获后继续
- [x] 4.2 幂等：每条 `id` 作为 `idempotency_key` 注入发布 payload，渠道层统一携带

## 5. 测试与回归

- [x] 5.1 `scripts/unit_checks.py`：新增渠道契约断言（`get_channel('mock')`、`publish` 返回结构化结果、`publish_off` 生效、幂等去重）
- [x] 5.2 `scripts/smoke_test.py`：迁移到 `MockChannel.publish` / `publish_off` 新契约，移除对 `rpa.submit_listing` 的直接依赖
- [x] 5.3 `scripts/ui_test.py`：适配批量 UI（多图上传、勾选、批量发布）
- [x] 5.4 全量回归：启动模拟后台 + Streamlit，跑通「单图」与「批量」两条完整链路（生成 → 审核 → 发布 → 下架）

## 6. 收尾

- [x] 6.1 确认 `app.py` / `smoke_test.py` 已迁移后删除 `src/rpa.py` 兼容层
- [x] 6.2 更新 README：功能特性、架构图（批量 + 渠道适配器 + 幂等）、面试讲解要点、FAQ（如何新增渠道）
- [x] 6.3 运行 `openspec validate batch-upload-and-channel-adapters` 校验变更通过