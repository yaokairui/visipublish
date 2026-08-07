## Context

现状：`src/vision_client.py` 的 `OpenAIVisionClient` 直接把 `VISION_API_BASE` 当作完整的 chat/completions 地址使用，并强制携带 `response_format=json_object`；`src/config.py` 对环境变量只做字符串透传。`src/rules.py` 的属性归一化只处理枚举类属性（material/style），自由文本 `color` 原样透传。接入 agnes-2.5-flash 网关时暴露两个问题：base 指向 `/v1` 导致 404；`response_format=json_object` 下模型返回「图像分析」schema 而非目标上架 JSON。动机详见 proposal.md。

## Goals / Non-Goals

**Goals:**
- 让 agnes-2.5-flash 这类 OpenAI 兼容网关开箱即用：base URL 归一、response_format 自适应、输出中文化。
- 保持 OpenAI 官方端点行为不变（回归验证）。
- 失败路径仍自动回退 Mock，且「识别引擎」标识与实际数据来源一致。

**Non-Goals:**
- 不引入新依赖（继续使用 requests，不引入 openai SDK）。
- 不支持多图 / 批量识别。
- 不改变 RPA 与模拟后台的行为（仅调整演示默认配置）。

## Decisions

1. **端点解析放在 config 层**：新增 `resolve_chat_completions_url(base)`，以 `/chat/completions` 结尾则直接使用，否则追加该路径。放 config 层便于单测与复用。备选：放在 vision_client 内部——但端点语义属于环境配置，config 是更合适的归属。
2. **response_format 自适应（行为探测，而非按网关域名判断）**：`OpenAIVisionClient.analyze` 先带 `response_format=json_object` 请求 → 解析 → 校验结果是否含 `category` 键；不满足则自动再发一次不带 `response_format` 的请求并解析。两层都失败则抛 `VisionError`，由 `analyze_image` 统一回退 Mock。备选：按 base 域名（含 "agnes" 等）跳过 json_object——脆弱，网关地址可变，行为探测更通用。
3. **系统提示词约束 + 规则层二次兜底**：系统提示词要求 category 取自枚举、color/material/style 使用简体中文；同时规则层对任何来源（API/Mock）统一做类目白名单回退与颜色别名归一化，不依赖模型自觉。
4. **颜色归一化放在规则层**：新增 `COLOR_ALIASES`（英文/常见变体 → 简体中文），在 `resolve_attributes` 中对 text 型属性（color）应用；choice 属性沿用既有白名单逻辑。Mock 与 API 两条链路共用同一兜底。
5. **演示默认值**：`.env.example` 以 agnes 网关为示例；`RPA_HEADLESS=false` 作为面试演示的可选配置写入说明。

## Risks / Trade-offs

- [agnes 模型在 json_object 模式下返回自定义图像分析 schema] → 通过「目标字段校验 + 降级重试」兜底；即便降级结果仍不理想，也由规则层归一化，不会产生脏标题。
- [降级请求可能返回非 JSON 文本] → `_parse_json` 已容忍 markdown 代码围栏与前后空白；仍失败则抛 `VisionError`，走 Mock 回退，流程不中断。
- [颜色别名无法覆盖全部变体] → 未命中时保留原值，不阻断生成流程。
- [额外的一次失败请求产生费用/延迟] → 仅当 json_object 结果不满足 schema 时发生；OpenAI 官方网关通常第一次即成功，不影响主流路径。

## Migration Plan

- 改动文件：`src/config.py`、`src/vision_client.py`、`src/rules.py`、`.env.example`；本地 `.env` 已配置 agnes 网关。
- 验证：先跑 `scripts/smoke_test.py`（Mock 链路回归）；再跑新增的 agnes 实调用验证与 `scripts/ui_test.py` 全流程。
- 回滚：恢复上述文件与 `.env.example` 即可，无数据迁移、无持久化变更。

## Open Questions

无。多图 / 批量识别等属于后续独立变更，不影响本变更的 spec、设计与任务拆分。