## Why

当前视觉识别按 OpenAI 官方端点硬编码：`VISION_API_BASE` 必须是完整的 `/chat/completions` 地址，且强制 `response_format=json_object`。接入 agnes-2.5-flash（OpenAI 兼容网关）时发现两个兼容性问题：base 指向 `/v1` 时请求 404；该模型在 `response_format=json_object` 下返回「图像分析」schema 而非目标上架 JSON。结果就是「明明配置了 Key，却静默回退到 Mock 识别」，识别引擎标识与实际行为不一致。

## What Changes

- `VISION_API_BASE` 兼容两种写法：`https://.../v1`（自动补全 `/chat/completions`）或完整端点 URL。
- 识别请求自适应：优先 `response_format=json_object`，解析后校验是否含目标字段；失败或 schema 不符时自动降级为普通请求重试。
- 系统提示词约束：类目必须取自枚举（T恤/连衣裙/牛仔裤/卫衣/运动鞋），color/material/style 使用简体中文，降低脏数据概率。
- 响应解析增强：容忍 markdown 代码围栏、前后空白、`choices[0].message.content` 缺失等异常。
- 颜色别名归一化：把模型常见的英文/变体颜色名映射为中文，保证标题与属性展示质量（规则层增强）。
- `.env` / `.env.example` 补充 agnes 网关示例，并默认 `RPA_HEADLESS=false` 便于面试演示。

## Capabilities

### New Capabilities
- `vision-recognition`: 商品图片识别为结构化 JSON（category/color/material/style），支持可配置的 OpenAI 兼容 Vision API 网关、自适应 `response_format`、健壮解析，以及失败时自动回退 Mock 识别。

### Modified Capabilities
<!-- 本仓库暂无既有 spec，无修改项 -->

## Impact

- 代码：`src/config.py`（端点解析）、`src/vision_client.py`（请求/解析/降级策略）、`src/rules.py`（颜色归一化）
- 配置：`.env`、`.env.example`（新增 agnes 网关示例与演示默认值）
- 依赖：无新增
- 兼容性：OpenAI 官方端点行为保持不变，需回归验证