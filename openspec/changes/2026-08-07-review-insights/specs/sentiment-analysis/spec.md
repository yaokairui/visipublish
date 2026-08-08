## Purpose

定义情感分析的行为契约：通过可插拔的 analyzer（lexicon / huggingface / llm）对单条评价返回结构化情感结果（sentiment / score / confidence / 可选维度标签），默认实现离线可用，llm 失败自动回退。

## ADDED Requirements

### Requirement: analyzer 契约

系统 SHALL 通过统一接口 `analyze(text) -> ReviewResult` 执行情感分析；`ReviewResult` 包含 `sentiment`（positive | negative | neutral）、`score`（0-1，越高越正向）、`confidence`（0-1）、可选 `labels`（维度标签列表）。调用方不感知具体实现。

#### Scenario: 分析一条差评
- **WHEN** 对「物流太慢了，等了一周」调用分析
- **THEN** 返回 `sentiment=negative` 且 `score < 0.5`

### Requirement: 可插拔实现与配置

系统 SHALL 通过 `ANALYZER` 环境变量选择实现（默认 `lexicon`）。v1 必须实现 `lexicon`（jieba + 电商情感词典，离线）；`huggingface`（`uer/roberta-base-finetuned-jd-binary-chinese`）与 `llm`（OpenAI 兼容 API）为未来可选实现，接入时应遵循同一 `analyze(text) -> ReviewResult` 契约，未实现时选择器返回明确错误而非静默降级。

#### Scenario: 默认实现离线可用
- **WHEN** 未配置 `ANALYZER` 或配置为 `lexicon`
- **THEN** 系统使用 lexicon 完成分析，无需任何外部依赖

#### Scenario: 切换实现（未来）
- **WHEN** v1.5 接入 `huggingface` / `llm` 且用户切换 `ANALYZER`
- **THEN** 系统按同一契约返回 `ReviewResult`，无需改动调用方

### Requirement: llm 维度标签（可选）

当使用 `llm` 实现时，系统 SHALL 额外输出维度标签：物流 / 质量 / 描述 / 售后 / 价格 / 其他，用于痛点归因。

#### Scenario: 差评含多个维度
- **WHEN** 对「包装破损，客服还态度差」调用 `llm` 分析
- **THEN** 返回 `labels` 同时包含质量与售后
