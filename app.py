"""
电商 AI 智能上架助手（面试演示 MVP）
====================================
Streamlit 前端：
  批量上传商品图片 -> AI 逐张识别结构化 JSON -> 运营规则库生成标题/属性/生图提示词
  -> 批量人工审核（可编辑、可勾选）-> 渠道适配器批量上架（默认 MockChannel + Playwright RPA）

启动：streamlit run app.py
"""
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

from src import config
from src.batch import publish_batch
from src.channels import get_channel
from src.listing_generator import generate_listing, listing_payload_for_rpa
from src.placeholder import make_placeholder
from src.rules import CATEGORY_OPTIONS, get_rule, get_rule_by_name
from src.title_ai import generate_ai_titles, resolve_title
from src.vision_client import analyze_image

st.set_page_config(page_title="电商 AI 智能上架助手", page_icon="🛒", layout="wide")

# ---------- 会话状态 ----------
SS = st.session_state
SS.setdefault("items", [])          # 批量商品记录列表
SS.setdefault("channel", get_channel())  # 按 CHANNEL 配置实例化的发布渠道

_STATUS_LABEL = {
    "pending": "待发布",
    "publishing": "发布中",
    "success": "已上架",
    "failed": "失败",
    "skipped": "已跳过",
    "delisted": "已下架",
}

_ATTR_LABEL = {
    "color": "颜色",
    "material": "材质",
    "style": "版型",
    "pattern": "图案",
    "use_case": "用途",
    "fabric": "面料",
    "sleeve": "袖长",
}


def _make_placeholders(listing: dict) -> list:
    """用 Pillow 生成 3 张占位图（不调用生图 API）。"""
    paths = []
    for i, prompt in enumerate(listing["prompts"], start=1):
        paths.append(str(make_placeholder(prompt, i, config.OUTPUT_DIR)))
    return paths


def _build_item(name: str, image_bytes: bytes, vision: dict) -> dict:
    """一条批量商品记录：识别结果 + 规则生成 + 审核/发布字段。"""
    listing = generate_listing(vision, 0)
    return {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "image": image_bytes,
        "vision": vision,
        "listing": listing,
        "seed": 0,
        "selected": True,
        "status": "pending",
        "error": "",
        "placeholders": _make_placeholders(listing),
        "ai_titles": [],
        "payload": None,
        "rpa_result": None,
        "backend_id": None,
    }


def _sync_widgets(item: dict) -> None:
    """把该条 listing 的最新值同步到带 key 的控件，保证审核区展示最新值。"""
    item_id = item["id"]
    listing = item["listing"]
    SS.setdefault(f"title_src_{item_id}", "ai-1" if item.get("ai_titles") else "rule")
    SS[f"title_{item_id}"] = listing["title"]
    SS[f"cat_{item_id}"] = listing["category"]
    for key, value in listing["attributes"].items():
        SS[f"attr_{item_id}_{key}"] = value
    for i, prompt in enumerate(listing["prompts"]):
        SS[f"prompt_{item_id}_{i}"] = prompt


def _build_payload(item: dict) -> dict:
    """从审核控件收集最终值，复用规则库的 payload 构造，避免契约重复。"""
    item_id = item["id"]
    listing = item["listing"]
    category = SS.get(f"cat_{item_id}", listing["category"])
    rule = get_rule_by_name(category)
    edited = dict(listing)
    edited.update(
        {
            "title": resolve_title(
                SS.get(f"title_src_{item_id}", "rule"),
                item.get("ai_titles") or [],
                listing["title"],
                SS.get(f"title_{item_id}", ""),
            ),
            "category": category,
            "attributes": {
                key: SS.get(f"attr_{item_id}_{key}", listing["attributes"].get(key, ""))
                for key in rule["attribute_spec"]
            },
            "prompts": [
                SS.get(f"prompt_{item_id}_{i}", p)
                for i, p in enumerate(listing["prompts"])
            ],
            "brand": rule["brand"],
        }
    )
    return listing_payload_for_rpa(edited)


# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("⚙️ 系统状态")
    if config.VISION_API_KEY:
        st.success("Vision API 已配置（真实识别）")
    else:
        st.warning("未配置 VISION_API_KEY\n\n将使用内置 Mock 识别（离线可演示）")
    st.info(
        f"发布渠道：`{SS.channel.name}`\n\n"
        f"模拟后台：{config.MOCK_BACKEND_URL}\n\n"
        f"RPA 模式：{'无头' if config.RPA_HEADLESS else '可见浏览器'}\n\n"
        f"批量上限：{config.BATCH_IMAGE_LIMIT} 张"
    )
    if st.button("🧹 清除会话", use_container_width=True):
        for key in list(SS.keys()):
            del SS[key]
        st.rerun()
    st.divider()


# ---------- 页头 ----------
st.title("🛒 电商 AI 智能上架助手")
st.caption(
    "批量上传商品图片 → AI 逐张识别结构化信息 → 运营规则生成标题 / 属性 / 生图提示词 "
    "→ 批量人工审核 → 渠道适配器自动上架（默认本地模拟后台）"
)

# ---------- 第一步：上传与生成 ----------
st.subheader("📥 1. 上传商品图片（可多选）")
uploaded_files = st.file_uploader(
    "选择一张或多张商品图（jpg / png / webp）",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    key="uploader",
)
if uploaded_files:
    st.write(f"已选择 {len(uploaded_files)} 张")
    if len(uploaded_files) > config.BATCH_IMAGE_LIMIT:
        st.warning(f"超过单批上限 {config.BATCH_IMAGE_LIMIT} 张，将只处理前 {config.BATCH_IMAGE_LIMIT} 张")
    preview_cols = st.columns(min(len(uploaded_files), 6))
    for col, f in zip(preview_cols, uploaded_files[:6]):
        with col:
            try:
                st.image(f.getvalue(), caption=f.name, width=130)
            except Exception:
                pass

if st.button("🚀 开始生成", type="primary", use_container_width=True):
    if not uploaded_files:
        st.warning("请先上传商品图片")
    else:
        files = uploaded_files[: config.BATCH_IMAGE_LIMIT]
        items = []
        with st.spinner(f"AI 正在逐张识别并生成标题（{len(files)} 张）..."):
            for f in files:
                try:
                    image_bytes = f.getvalue()
                    vision = analyze_image(image_bytes)
                    item = _build_item(f.name, image_bytes, vision)
                    if config.VISION_API_KEY and item.get("listing"):
                        rule = get_rule(item["listing"]["category_key"])
                        item["ai_titles"] = generate_ai_titles(image_bytes, vision, rule)
                    _sync_widgets(item)
                    items.append(item)
                except Exception as exc:  # 单张失败不中断整批
                    items.append(
                        {
                            "id": uuid.uuid4().hex[:12],
                            "name": f.name,
                            "image": None,
                            "vision": None,
                            "listing": None,
                            "seed": 0,
                            "selected": False,
                            "status": "skipped",
                            "error": str(exc),
                            "placeholders": [],
                            "payload": None,
                            "rpa_result": None,
                            "backend_id": None,
                        }
                    )
        SS["items"] = items
        st.rerun()

# ---------- 第二步：批量审核队列 ----------
st.divider()
st.subheader("🧾 2. 批量审核队列")
if not SS["items"]:
    st.info(
        "上传图片后点击【开始生成】。未配置 API Key 时自动使用 Mock 识别，离线即可跑通全流程。"
    )
else:
    overview = pd.DataFrame(
        [
            {
                "文件名": it["name"],
                "标题": (it["listing"] or {}).get("title", ""),
                "类目": (it["listing"] or {}).get("category", ""),
                "状态": _STATUS_LABEL.get(it["status"], it["status"]),
            }
            for it in SS["items"]
        ]
    )
    st.dataframe(overview, use_container_width=True, hide_index=True)
    selected_count = sum(1 for it in SS["items"] if it.get("selected"))
    st.caption(f"已勾选 {selected_count} / {len(SS["items"])} 条待上架")

    for item in SS["items"]:
        item_id = item["id"]
        with st.expander(f"🖼 {item['name']} — {_STATUS_LABEL.get(item['status'], item['status'])}"):
            item["selected"] = st.checkbox(
                "✅ 勾选上架", value=item.get("selected", True), key=f"sel_{item_id}"
            )
            if item["status"] == "skipped" or item["listing"] is None:
                st.error(f"该图片生成失败：{item.get('error')}")
                continue

            listing = item["listing"]
            rule = get_rule_by_name(listing["category"])
            col_img, col_edit = st.columns([1, 2.2])
            with col_img:
                if item.get("image"):
                    st.image(item["image"], caption="原图", width=140)
                _src = (item.get("vision") or {}).get("source", "unknown")
                _note = (item.get("vision") or {}).get("note", "")
                if _src == "api":
                    st.caption(f"🤖 识别来源：真实 Vision API（{config.VISION_MODEL}）")
                elif _src == "mock":
                    st.caption("🛠 识别来源：内置 Mock（未配置 API Key 或 API 失败）")
                if _note:
                    st.caption(f"⚠️ {_note}")
            with col_edit:
                st.markdown("**生成标题（可选来源）**")
                _src_opts = []
                for _i, _t in enumerate(item.get("ai_titles") or [], start=1):
                    _src_opts.append((f"ai-{_i}", f"✨ AI 标题 {_i}：{_t}"))
                _src_opts.append(("rule", f"📐 规则模板：{listing['title']}"))
                _src_opts.append(("manual", "✍️ 手动输入"))
                _src_keys = [k for k, _ in _src_opts]
                _src_labels = {k: v for k, v in _src_opts}
                st.selectbox(
                    "标题来源",
                    _src_keys,
                    format_func=lambda k: _src_labels[k],
                    key=f"title_src_{item_id}",
                )
                _cur_src = SS.get(f"title_src_{item_id}", "rule")
                if _cur_src == "manual":
                    st.text_input("商品标题（手动输入）", key=f"title_{item_id}")
                else:
                    st.caption(
                        f"当前标题：{resolve_title(_cur_src, item.get('ai_titles') or [], listing['title'])}"
                    )
                if not item.get("ai_titles"):
                    st.caption("⚠️ AI 标题不可用（未配置 API Key 或生成失败），已回退规则模板标题")
                st.markdown("**商品类目**")
                st.selectbox("商品类目", CATEGORY_OPTIONS, key=f"cat_{item_id}")

            with st.expander("🔍 识别原始 JSON（AI 返回）"):
                st.json(item.get("vision") or {})

            st.markdown("**商品属性（可修改）**")
            attr_spec = rule["attribute_spec"]
            attr_cols = st.columns(len(attr_spec) or 1)
            for col, (key, meta) in zip(attr_cols, attr_spec.items()):
                with col:
                    label = _ATTR_LABEL.get(key, key)
                    if meta["type"] == "choice":
                        st.selectbox(label, meta["options"], key=f"attr_{item_id}_{key}")
                    else:
                        st.text_input(label, key=f"attr_{item_id}_{key}")

            st.markdown("**AI 生图提示词 × 3（可修改，未调用生图 API）**")
            for i in range(3):
                st.text_area(f"提示词 {i + 1}", key=f"prompt_{item_id}_{i}", height=72)

            if item.get("placeholders"):
                st.markdown("**AI 生图占位图（Pillow 生成）**")
                ph_cols = st.columns(3)
                for col, path, i in zip(ph_cols, item["placeholders"], range(1, 4)):
                    with col:
                        st.image(path, caption=f"占位图 {i}", width=190)

            act_col, note_col = st.columns([1, 3])
            with act_col:
                regen = st.button("🔄 重新生成", key=f"regen_{item_id}", use_container_width=True)
            with note_col:
                st.caption("【重新生成】仅轮换本条核心卖点并重跑规则，其他条目不受影响。")
            if regen:
                item["seed"] += 1
                item["listing"] = generate_listing(item["vision"], item["seed"])
                item["placeholders"] = _make_placeholders(item["listing"])
                item["status"] = "pending"
                item["error"] = ""
                _sync_widgets(item)
                st.rerun()

            if item["status"] in ("success", "delisted"):
                d_col, d_note = st.columns([1, 3])
                with d_col:
                    delist = st.button("🗑 下架", key=f"delist_{item_id}", use_container_width=True)
                with d_note:
                    st.caption(f"后端记录 ID：{item.get('backend_id') or '（未知）'}")
                if delist:
                    res = SS.channel.publish_off({"backend_id": item.get("backend_id")})
                    if res.success:
                        item["status"] = "delisted"
                        st.success(res.message)
                        st.rerun()
                    else:
                        st.error(res.message)

            if item["status"] == "failed":
                st.error(f"发布失败：{item.get('error')}")
            if item.get("rpa_result"):
                with st.expander("📋 RPA 执行日志"):
                    for step in item["rpa_result"].get("steps", []):
                        st.markdown(f"- {step}")
                    st.markdown(
                        f"**提交时间**：{item['rpa_result'].get('submitted_at')}　|　"
                        f"**目标页面**：{item['rpa_result'].get('url')}"
                    )
                    if (
                        item["rpa_result"].get("screenshot")
                        and Path(item["rpa_result"]["screenshot"]).exists()
                    ):
                        st.image(item["rpa_result"]["screenshot"], caption="RPA 浏览器截图", width=520)

# ---------- 第三步：批量上架 ----------
st.divider()
st.subheader("🚀 3. 批量上架")
if SS["items"]:
    ready, ready_msg = SS.channel.check_ready()
    if not ready:
        st.error(f"❌ 渠道不可用：{ready_msg}")
    pending_selected = [
        it for it in SS["items"]
        if it.get("selected") and it.get("status") not in ("success", "delisted")
    ]
    if pending_selected:
        names = "、".join(it["name"] for it in pending_selected[:5])
        if len(pending_selected) > 5:
            names += f" 等 {len(pending_selected)} 条"
        st.caption(f"待上架：{names}")

    if st.button("✅ 确认无误，批量上架", type="primary", use_container_width=True, disabled=not ready):
        if not pending_selected:
            st.warning("没有勾选的待上架条目")
        else:
            for it in pending_selected:
                it["payload"] = _build_payload(it)
            progress = st.progress(0.0, text="开始批量上架...")

            def _progress(i: int, total: int, item: dict) -> None:
                progress.progress(i / total, text=f"正在上架 {i}/{total}：{item['name']}")

            publish_batch(SS.channel, pending_selected, progress_cb=_progress)
            st.rerun()

    done_items = [it for it in SS["items"] if it["status"] in ("success", "failed")]
    if done_items:
        ok_n = sum(1 for it in done_items if it["status"] == "success")
        st.markdown(f"**批量结果**：成功 {ok_n} / 失败 {len(done_items) - ok_n}")
        for it in done_items:
            if it["status"] == "success":
                st.success(f"✅ {it['name']} — {(it.get('rpa_result') or {}).get('message', '上架成功')}")
            else:
                st.error(f"❌ {it['name']} — {it.get('error')}")
        st.markdown(f"📊 查看后台记录：[已上架记录]({config.MOCK_BACKEND_URL}/submissions)")

# ---------- 架构说明 ----------
with st.expander("🧩 系统架构与数据流"):
    st.markdown(
        """
```
┌────────────┐   ┌──────────────────┐   ┌─────────────────┐   ┌──────────────────┐
│  Streamlit  │   │  Vision API /    │   │  运营规则库       │   │  渠道适配器        │
│ 批量上传图片  │──▶│  Mock 识别(离线)  │──▶│  标题/属性/提示词  │──▶│  MockChannel(RPA) │──▶ 模拟电商后台
└────────────┘   └──────────────────┘   └────────┬────────┘   └──────────────────┘
                                                 │ 批量审核（可编辑 / 勾选）
                                                 ▼
                                    批量发布（串行 + 失败隔离 + 幂等）
```
"""
    )
    st.markdown(
        """
- **识别层**：配置 `VISION_API_KEY` 走真实多模态 API；未配置自动回退 Mock（Pillow 主色分析），保证离线演示。
- **规则层**：`src/rules.py` 内置「类目规则」——标题模板（季节+品牌+商品名+核心卖点）、属性白名单、提示词模板。
- **审核层**：批量队列逐条可编辑、可勾选，单条「重新生成」只影响本条；「AI 生成 ≠ 自动发布」。
- **渠道层**：`src/channels/` 统一契约（登录 / 上架 / 下架 / 状态检查）；`MockChannel` 用 Playwright 填表，带重试、回读校验、失败截图；`ApiChannel` 为官方 API 骨架。
- **批量层**：`src/batch.py` 按勾选顺序串行发布，单条失败隔离，`idempotency_key` 防重复上架。
        """
    )