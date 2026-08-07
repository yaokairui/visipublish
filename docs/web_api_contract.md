# Web 前端 API 契约（FastAPI 后端 ↔ React 前端）

> 供并行开发对齐用。后端：`webapp/`（FastAPI，端口 8502）；前端：`frontend/`（Vite + React）。
> 会话：客户端创建后每次请求带 `X-Session-Id` 头。所有响应 JSON 使用 UTF-8。

## 通用约定

- 会话存储在服务端内存（dict：session_id -> items 列表），单用户演示足够。
- Item 结构（后端持有）：

```json
{
  "id": "str",
  "name": "文件名",
  "status": "pending|publishing|success|failed|skipped|delisted",
  "error": "",
  "selected": true,
  "category": "T恤",
  "attributes": {"color": "红色", "material": "纯棉", "style": "基础款"},
  "prompts": ["p1", "p2", "p3"],
  "ai_titles": ["AI 标题1", "AI 标题2", "AI 标题3"],
  "rule_title": "规则模板标题",
  "title_source": "ai-1|ai-2|ai-3|rule|manual",
  "manual_title": "",
  "title": "已解析的最终标题（后端用 resolve_title 解析）",
  "vision": {"category": "...", "color": "...", "material": "...", "style": "...", "source": "api|mock"},
  "placeholders": ["/api/placeholders/{id}/1", "/api/placeholders/{id}/2", "/api/placeholders/{id}/3"],
  "rpa_result": null,
  "backend_id": null
}
```

## 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/session | 创建会话，返回 `{"session_id": "uuid"}` |
| GET | /api/config | 返回 `{"vision_configured": bool, "vision_model": str, "channel": str, "mock_backend_url": str, "rpa_headless": bool, "batch_limit": int, "ai_title_count": int, "title_max_len": int, "categories": ["T恤",...], "category_rules": [{"name":"T恤","attribute_spec":{"color":{"type":"text","default":"白色"},"material":{"type":"choice","options":[...],"default":"纯棉"},...}}], "attribute_labels": {"color":"颜色","material":"材质","style":"版型"}}`（category_rules 供前端按类目渲染属性编辑器，attribute_labels 供字段中文名） |
| GET | /api/items | 当前会话全部 items |
| POST | /api/generate | multipart 上传 `files`（可多张，超 batch_limit 截断）。同步逐张识别+生成（含 AI 标题），返回 `{"items": [Item]}`。单张失败 -> status=skipped 不中断 |
| POST | /api/items/{id}/review | body `{"title_source": str, "manual_title": str, "category": str, "attributes": dict, "prompts": [str], "selected": bool}`；后端校验白名单（resolve_attributes）、用 resolve_title 重算 title，返回 `{"item": Item}` |
| POST | /api/items/{id}/regen | 该条 seed+1 重跑规则模板（AI 标题不变），返回 `{"item": Item}` |
| POST | /api/items/{id}/delist | 调用渠道 publish_off，返回 `{"ok": bool, "message": str}` |
| POST | /api/publish | body `{"item_ids": [str]}`；后台线程执行 publish_batch，返回 `{"job_id": "str"}` |
| GET | /api/publish/{job_id} | `{"running": bool, "total": int, "success": int, "failed": int, "items": [{"id","status","error","message","title"}]}`，前端 1s 轮询 |
| GET | /api/placeholders/{item_id}/{index} | 返回占位图 PNG（FileResponse） |
| DELETE | /api/session | 清空当前会话数据 |

## 后端实现要点

- 依赖：fastapi、uvicorn、python-multipart；复用 `src/`（analyze_image / generate_listing / get_rule / get_rule_by_name / listing_payload_for_rpa / resolve_attributes / make_placeholder / get_channel / publish_batch / generate_ai_titles / resolve_title / config）。
- 发布 job：threading.Thread 跑 publish_batch（channel 复用单例），进度写回 item 字典；轮询接口直接读。
- title 解析：`resolve_title(title_source, ai_titles, rule_title, manual_title)`；category 变更后 attributes 用 `get_rule_by_name(category)["attribute_spec"]` 白名单重算（保留已填的合法值，非法回退默认）。
- 静态托管：若 `frontend/dist` 存在，挂载为 `/`（前端构建产物）；否则根路径返回 API 说明 JSON。
- CORS：允许 `http://localhost:5173`（vite dev）。
- 端口 8502。日志输出到 stdout。

## 前端实现要点（设计系统：AI-Native 暗色运维风）

- 技术栈：Vite + React + TypeScript + Tailwind CSS + lucide-react（图标一律用 SVG，禁用 emoji 图标）。
- 设计令牌（CSS 变量）：primary #0F172A、accent #16A34A（运行绿）、destructive #DC2626、warning amber #F59E0B、background #020617、foreground #F8FAFC、muted #1A1E2F、border #334155。
- 字体：Fira Sans（正文）+ Fira Code（数据/代码）。
- 布局：左侧边栏（系统状态：识别模式、渠道、批量上限；清除会话）+ 主区三步流程（1 上传 → 2 审核队列 → 3 批量上架）。
- 上传：多文件拖拽区 + 缩略图网格 + 开始生成按钮（loading 态）。
- 审核：概览表格 + 可展开行编辑（标题来源 select、标题/类目/属性/提示词编辑、单条重新生成、下架、RPA 日志）。
- 上架：勾选汇总、确认按钮、进度条、逐条成功/失败结果；轮询 /api/publish/{job_id}。
- 交互：150-300ms 过渡、loading spinner/骨架、Toast 反馈、focus 可见、cursor-pointer、prefers-reduced-motion 尊重。
- 构建：`npm run build` 输出到 `frontend/dist`（FastAPI 托管）。
- dev：vite 代理 `/api` -> `http://127.0.0.1:8502`。