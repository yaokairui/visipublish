## 1. 端点与配置

- [x] 1.1 在 `src/config.py` 新增 `resolve_chat_completions_url()`，兼容 `/v1` 根地址与完整端点两种写法
- [x] 1.2 更新 `.env.example` 与 `.env`，以 agnes 网关为示例（`VISION_API_BASE=https://apihub.agnes-ai.com/v1`、`VISION_MODEL=agnes-2.5-flash`、`RPA_HEADLESS=false`）

## 2. 视觉识别兼容

- [x] 2.1 `OpenAIVisionClient` 请求改为自适应 `response_format`：先带 `json_object`，解析校验含 `category` 后降级为普通请求重试
- [x] 2.2 强化系统提示词：类目枚举约束 + color/material/style 简体中文约束
- [x] 2.3 增强 `_parse_json` 容忍 markdown 代码围栏与空白；`analyze_image` 真实 API 失败时回退 Mock 并标注来源

## 3. 规则层归一化

- [x] 3.1 `src/rules.py` 新增 `COLOR_ALIASES`（英文/常见变体 → 简体中文）
- [x] 3.2 `resolve_attributes` 对 text 型属性应用颜色归一化，与 choice 白名单逻辑共用

## 4. 验证

- [x] 4.1 用测试图实测 agnes-2.5-flash：返回 JSON 含 category/color/material/style，category 归一化到类目枚举内
- [x] 4.2 运行 `scripts/smoke_test.py`（Mock 链路回归）与 `scripts/ui_test.py`（全流程回归）
- [x] 4.3 `openspec validate` 校验通过