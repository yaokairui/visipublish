# VisiPublish 界面主题约定

三个子项目（运营看板 / 电商 AI 上架助手 / 评价分析）与导航页统一支持 **明亮 / 暗黑**
两种主题，并保证「从导航页点开哪个项目，默认就是导航页当前主题」。

## 生效顺序

1. URL 查询参数 `?theme=light|dark`（导航页跳转时自动附加）——最高优先级
2. `localStorage['visipublish-theme']`（同源记忆上次选择）
3. 默认值：`dark`（导航页默认深色科技风）

## 实现约定

- 主题状态挂在 `<html data-theme="light|dark">` 上；所有主题相关 CSS 都基于
  `data-theme` 或 CSS 变量实现，不在 body 上随意加 class。
- 每个页面右上角固定一个主题切换按钮（SVG 太阳/月亮图标，`aria-label="切换主题"`，
  `title="切换明亮/暗黑"`），z-index 足够高（≥ 40），点击后：
  1. 切换 `<html data-theme>`；
   2. 写入 `localStorage['visipublish-theme']`；
  3. 用 `history.replaceState` 更新当前 URL 的 `theme` 参数（便于返回/刷新保持）。
- 深色为主题默认形态（深空蓝底 + 绿色/青色强调 + 科技感网格光晕）；浅色为同色相、
  对比度达标（正文 ≥ 4.5:1）的亮色变体。
- 深色：背景 `#0B1120`（运营看板 `#070D1A`），卡片 `#111C31` 系，边框
  `rgba(148,163,184,.14)`，强调绿 `#22C55E` / 青 `#22D3EE`。
- 浅色：背景 `#F1F5F9` 系，卡片白色，边框 `#E2E8F0`，正文 `#1E293B`/`#475569`。
- 字体：中文使用 `PingFang SC / Microsoft YaHei` 系统字体，数字用等宽
  （tabular-nums / JetBrains Mono / Fira Code）；正文 400/500 字重、行高 1.5-1.7、
  `-webkit-font-smoothing: antialiased`，避免过重字重与过高对比造成的「锐化感」。

## 导航页链接格式

导航页的项目卡片/页脚链接统一为：

```html
<a href="...入口路径?theme=dark">…</a>   <!-- theme 由当前导航页主题动态生成 -->
```

子项目加载时先解析 `?theme=`，再回退 `localStorage`，并把自己的切换结果写回
`localStorage['visipublish-theme']`，保证来回切换体验一致。
