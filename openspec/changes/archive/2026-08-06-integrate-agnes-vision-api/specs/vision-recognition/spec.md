## Purpose

定义商品图片识别为结构化上架数据的行为契约：通过可配置的 OpenAI 兼容多模态网关返回类目/颜色/材质/风格字段，并保证输出可被运营规则库安全消费，识别失败时自动回退内置 Mock。

## ADDED Requirements

### Requirement: 图片识别返回结构化 JSON

系统 SHALL 接受一张商品图片，并返回包含 category、color、material、style 四个字符串字段的结构化 JSON。

#### Scenario: 成功识别
- **WHEN** 用户上传一张可解析的商品图片并触发识别
- **THEN** 系统返回包含 category、color、material、style 字段的 JSON 对象

#### Scenario: 图片不可解析
- **WHEN** 上传的图片文件损坏或无法被解码
- **THEN** 系统抛出识别错误，且不返回伪造的结构化数据

### Requirement: 支持可配置的 OpenAI 兼容网关

系统 SHALL 通过环境变量配置视觉识别网关：`VISION_API_KEY`、`VISION_API_BASE`、`VISION_MODEL`。`VISION_API_BASE` 既可以是服务根地址（如 `https://.../v1`），也可以是完整的 chat completions 端点 URL，系统 SHALL 都能正确发起请求。

#### Scenario: base 指向服务根地址
- **WHEN** `VISION_API_BASE` 配置为 `https://example.com/v1`
- **THEN** 系统向 `https://example.com/v1/chat/completions` 发起识别请求

#### Scenario: base 为完整端点
- **WHEN** `VISION_API_BASE` 配置为 `https://example.com/v1/chat/completions`
- **THEN** 系统直接使用该地址发起识别请求，不重复拼接路径

### Requirement: response_format 自适应降级

系统 SHALL 优先以 `response_format=json_object` 请求识别；当该模式导致请求失败或返回内容不包含目标字段时，系统 SHALL 自动降级为不带 `response_format` 的普通请求并再次解析。

#### Scenario: 网关不支持 json_object
- **WHEN** 识别网关对 `response_format=json_object` 返回错误
- **THEN** 系统自动使用不带 `response_format` 的请求重试并成功返回结构化 JSON

#### Scenario: json_object 返回 schema 不符
- **WHEN** 网关在 `response_format=json_object` 下返回了不包含 category/color/material/style 的 JSON
- **THEN** 系统将该结果视为无效，自动降级重试并得到符合目标 schema 的 JSON

### Requirement: 输出约束与归一化

系统 SHALL 要求识别结果中的 category 来自运营规则库的类目枚举；对枚举外的类目值，系统 SHALL 回退到默认类目。系统 SHALL 将常见的英文/变体颜色名归一化为简体中文颜色名，保证标题与属性展示一致性。

#### Scenario: 模型返回枚举外类目
- **WHEN** 识别结果中 category 为「Abstract」等不在类目枚举中的值
- **THEN** 系统回退到默认类目「T恤」并继续生成标题与属性

#### Scenario: 模型返回英文颜色
- **WHEN** 识别结果中 color 为「Red」「White」等英文颜色名
- **THEN** 系统输出对应的中文颜色名（如「红色」「白色」）

### Requirement: 识别失败自动回退 Mock

当未配置 `VISION_API_KEY`，或真实 API 调用与降级重试均失败时，系统 SHALL 自动使用内置 Mock 识别（颜色取自真实像素主色分析，类目/材质/风格使用内置演示默认值），并在结果中标注识别来源，保证离线演示不中断。

#### Scenario: 未配置 API Key
- **WHEN** `VISION_API_KEY` 为空
- **THEN** 系统使用 Mock 识别并返回带 source=mock 标注的结构化 JSON

#### Scenario: 真实 API 全部失败
- **WHEN** 真实 API 与降级重试均失败
- **THEN** 系统回退到 Mock 识别，并在结果中注明已自动回退