## Purpose

定义评价分析看板的行为契约：FastAPI 托管静态前端，围绕导入的评价数据渲染情感分布、差评率趋势、平台/商品对比、痛点词云与差评明细，并提供平台 / 商品 / 星级 / 日期筛选联动。界面明示数据仅在本机分析、不上传。

## ADDED Requirements

### Requirement: 看板可视化

系统 SHALL 在导入并分析后渲染：情感分布（环形图）、差评率趋势（按日/周折线）、平台与商品维度对比（柱状图）、痛点词云与 TopN 列表、差评明细表（含原文 / 星级 / 情感 / 商品 / 平台 / 日期）。

#### Scenario: 导入演示数据
- **WHEN** 用户点击「恢复示例数据」
- **THEN** 看板渲染全部图表与明细表，无空白区块

### Requirement: 筛选联动

系统 SHALL 支持平台 / 商品 / 星级 / 日期范围筛选；任一筛选变化时，全部图表与明细表实时联动刷新。

#### Scenario: 只看差评
- **WHEN** 用户把星级筛选改为 1-2 星
- **THEN** 情感分布、痛点词云与明细表仅基于差评数据刷新

### Requirement: 本地隐私提示

界面 SHALL 明示「数据仅在本机分析，不上传任何服务器」，并在导入区提示使用自己店铺后台导出的数据。

#### Scenario: 首次打开
- **WHEN** 用户打开看板
- **THEN** 页面上可见本地隐私提示与导入说明

### Requirement: 数据接口

系统 SHALL 提供接口：`POST /api/session` 创建内存会话、`POST /api/import` 导入（文件或文本）、`POST /api/analyze` 批量分析、`GET /api/summary`、`GET /api/pain-points`、`GET /api/reviews`（支持筛选参数）。

#### Scenario: 导入后获取摘要
- **WHEN** 用户导入并分析完成
- **THEN** `GET /api/summary` 返回总条数 / 好评率 / 差评率 / 平均星级等摘要指标
