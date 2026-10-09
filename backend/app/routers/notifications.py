"""Mobile dispatch alerts — webhook push with in-memory poll fallback."""
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel

from app import schemas

load_dotenv()

router = APIRouter()

_seq = 0
_latest: Optional[Dict[str, Any]] = None


def _next_id() -> str:
    global _seq
    _seq += 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"notif_{stamp}_{_seq:03d}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LatestNotificationResponse(BaseModel):
    notification: Optional[Dict[str, Any]] = None


@router.post("/notifications/dispatch-alert", response_model=schemas.DispatchAlertResponse)
def dispatch_alert(body: schemas.DispatchAlertRequest):
    """
    Fire a mobile alert at the exact enforcement-dispatch moment.
    Prefers MOBILE_WEBHOOK_URL; always stores the last alert for GET /notifications/latest.
    Never raises — failed push returns status=failed so the simulator can continue.
    """
    notification_id = _next_id()
    delivered_at = _utc_now_iso()
    payload = body.model_dump()
    payload["notification_id"] = notification_id
    payload["delivered_at"] = delivered_at
    if not payload.get("message"):
        payload["message"] = f"AQI alert — enforcement dispatched to {body.station_name}"

    webhook_url = (os.getenv("MOBILE_WEBHOOK_URL") or "").strip()
    webhook_secret = (os.getenv("MOBILE_WEBHOOK_SECRET") or "").strip()

    channel = "poll"
    error: Optional[str] = None
    status = "sent"

    if webhook_url:
        channel = "webhook"
        headers = {"Content-Type": "application/json"}
        if webhook_secret:
            headers["X-Aervia-Secret"] = webhook_secret
        try:
            resp = requests.post(webhook_url, json=payload, headers=headers, timeout=5)
            if resp.status_code >= 400:
                status = "failed"
                error = f"webhook HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as exc:
            status = "failed"
            error = str(exc)
        print(f"[notifications] webhook {status} id={notification_id} url={webhook_url} error={error}")
    else:
        print(f"[notifications] stored for poll id={notification_id} station={body.station_name}")

    payload["status"] = status
    payload["channel"] = channel
    if error:
        payload["error"] = error

    global _latest
    _latest = payload

    return schemas.DispatchAlertResponse(
        status=status,
        notification_id=notification_id,
        channel=channel,
        delivered_at=delivered_at,
        error=error,
    )


@router.get("/notifications/latest", response_model=LatestNotificationResponse)
def latest_notification(since: Optional[str] = None):
    """Return the last dispatch alert. Optional `since` ISO timestamp skips older records."""
    if _latest is None:
        return LatestNotificationResponse(notification=None)
    if isinstance(since, str) and since:
        delivered = _latest.get("delivered_at") or ""
        if delivered <= since:
            return LatestNotificationResponse(notification=None)
    return LatestNotificationResponse(notification=_latest)
