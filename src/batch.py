"""批量发布逻辑：按勾选顺序串行发布，单条失败隔离，支持进度回调。

item 结构（session_state 中的一条商品记录）：
    id / image / vision / listing / selected / status / error / payload ...
状态机：pending -> publishing -> success | failed | skipped
"""
from src.channels.base import BaseChannel, ChannelResult


def publish_batch(
    channel: BaseChannel,
    items: list[dict],
    progress_cb=None,
) -> dict:
    """按勾选顺序串行发布；单条异常捕获后继续，返回汇总。

    progress_cb(i, total, item) 可选，用于 Streamlit 进度条。
    幂等：每条记录的 id 作为 idempotency_key 注入 payload。
    """
    targets = [
        item
        for item in items
        if item.get("selected") and item.get("status") not in ("success", "delisted")
    ]
    summary = {
        "total": len(targets),
        "success": 0,
        "failed": 0,
        "results": [],
    }
    for i, item in enumerate(targets, start=1):
        item["status"] = "publishing"
        item["error"] = ""
        if progress_cb:
            progress_cb(i, len(targets), item)
        try:
            payload = dict(item.get("payload") or {})
            payload["idempotency_key"] = item["id"]
            result = channel.publish(payload)
            item["rpa_result"] = (
                result.to_dict() if isinstance(result, ChannelResult) else dict(result or {})
            )
            if result.success:
                item["status"] = "success"
                item["backend_id"] = (result.extra or {}).get("record_id")
                summary["success"] += 1
            else:
                item["status"] = "failed"
                item["error"] = result.message
                summary["failed"] += 1
        except Exception as exc:  # 单条异常隔离，继续后续条目
            item["status"] = "failed"
            item["error"] = str(exc)
            summary["failed"] += 1
        summary["results"].append(
            {
                "id": item["id"],
                "title": (item.get("payload") or {}).get("title", ""),
                "status": item["status"],
                "message": item.get("error")
                or (item.get("rpa_result") or {}).get("message", ""),
            }
        )
    return summary