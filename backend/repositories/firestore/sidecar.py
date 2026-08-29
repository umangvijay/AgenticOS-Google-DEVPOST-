"""Firestore stores for vault, settings, schedules, tokens, notifications, audit.

Used when STORAGE_BACKEND=firestore so Cloud Run has the same features as local SQLite.
Ciphertext only — SecretsVault still does AES-256-GCM.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.repositories.base import (
    BaseAuditRepository,
    BaseNotificationRepository,
    BaseRefreshTokenRepository,
    BaseScheduleRepository,
    BaseSecretsRepository,
    BaseSettingsRepository,
)
from backend.repositories.firestore.database import FirestoreDB
from backend.repositories.sqlite.settings_repository import DEFAULT_SETTINGS


async def _db():
    return await FirestoreDB.get_client()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FirestoreSecretsRepository(BaseSecretsRepository):
    async def store_secret(self, user_id: str, key: str, encrypted_value: str) -> None:
        db = await _db()
        doc_id = f"{user_id}::{key}"
        await db.collection("vault_secrets").document(doc_id).set(
            {
                "user_id": user_id,
                "key": key,
                "encrypted_value": encrypted_value,
                "updated_at": _now(),
            }
        )

    async def get_secret(self, user_id: str, key: str) -> Optional[str]:
        db = await _db()
        doc = await db.collection("vault_secrets").document(f"{user_id}::{key}").get()
        if not doc.exists:
            return None
        return (doc.to_dict() or {}).get("encrypted_value")

    async def delete_secret(self, user_id: str, key: str) -> bool:
        db = await _db()
        ref = db.collection("vault_secrets").document(f"{user_id}::{key}")
        snap = await ref.get()
        if not snap.exists:
            return False
        await ref.delete()
        return True

    async def list_secret_keys(self, user_id: str) -> List[str]:
        db = await _db()
        keys = []
        async for doc in db.collection("vault_secrets").where("user_id", "==", user_id).stream():
            data = doc.to_dict() or {}
            if data.get("key"):
                keys.append(data["key"])
        return sorted(keys)


class FirestoreSettingsRepository(BaseSettingsRepository):
    async def get_settings(self, user_id: str) -> Dict[str, Any]:
        db = await _db()
        doc = await db.collection("user_settings").document(user_id).get()
        stored = (doc.to_dict() or {}).get("settings") if doc.exists else {}
        if not isinstance(stored, dict):
            stored = {}
        return {**DEFAULT_SETTINGS, **stored}

    async def update_settings(self, user_id: str, updates: Dict[str, Any]) -> None:
        merged = {**(await self.get_settings(user_id)), **updates}
        db = await _db()
        await db.collection("user_settings").document(user_id).set(
            {"user_id": user_id, "settings": merged, "updated_at": _now()}
        )


class FirestoreScheduleRepository(BaseScheduleRepository):
    async def create_schedule(self, schedule_data: Dict[str, Any]) -> None:
        db = await _db()
        sid = schedule_data["schedule_id"]
        payload = dict(schedule_data)
        payload.setdefault("created_at", _now())
        payload["updated_at"] = _now()
        await db.collection("schedules").document(sid).set(payload)

    async def get_schedule(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        db = await _db()
        doc = await db.collection("schedules").document(schedule_id).get()
        return doc.to_dict() if doc.exists else None

    async def list_schedules(self, user_id: str) -> List[Dict[str, Any]]:
        db = await _db()
        out = []
        async for doc in db.collection("schedules").where("user_id", "==", user_id).stream():
            out.append(doc.to_dict() or {})
        return out

    async def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> None:
        if not updates:
            return
        db = await _db()
        updates = dict(updates)
        updates["updated_at"] = _now()
        await db.collection("schedules").document(schedule_id).set(updates, merge=True)

    async def delete_schedule(self, schedule_id: str) -> bool:
        db = await _db()
        ref = db.collection("schedules").document(schedule_id)
        snap = await ref.get()
        if not snap.exists:
            return False
        await ref.delete()
        return True

    async def list_due_schedules(self, now_iso: str) -> List[Dict[str, Any]]:
        db = await _db()
        due = []
        async for doc in db.collection("schedules").stream():
            row = doc.to_dict() or {}
            if str(row.get("status") or "").upper() != "ACTIVE":
                continue
            nxt = row.get("next_run_at")
            if nxt and nxt <= now_iso:
                due.append(row)
        return due

    async def record_execution(self, schedule_id: str, run_id: str, status: str) -> None:
        db = await _db()
        eid = str(uuid.uuid4())
        await db.collection("schedule_executions").document(eid).set(
            {
                "schedule_id": schedule_id,
                "run_id": run_id,
                "status": status,
                "triggered_at": _now(),
            }
        )
        await db.collection("schedules").document(schedule_id).set(
            {"last_run_at": _now(), "updated_at": _now()}, merge=True
        )

    async def get_execution_history(self, schedule_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        db = await _db()
        rows = []
        async for doc in (
            db.collection("schedule_executions").where("schedule_id", "==", schedule_id).stream()
        ):
            rows.append(doc.to_dict() or {})
        rows.sort(key=lambda r: r.get("triggered_at") or "", reverse=True)
        return rows[:limit]


class FirestoreRefreshTokenRepository(BaseRefreshTokenRepository):
    async def store_token(self, user_id: str, token_hash: str, expires_at: datetime) -> None:
        db = await _db()
        await db.collection("refresh_tokens").document(token_hash).set(
            {
                "user_id": user_id,
                "token_hash": token_hash,
                "expires_at": expires_at.isoformat() if hasattr(expires_at, "isoformat") else str(expires_at),
                "created_at": _now(),
            }
        )

    async def validate_and_consume(self, token_hash: str) -> Optional[str]:
        db = await _db()
        ref = db.collection("refresh_tokens").document(token_hash)
        doc = await ref.get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        exp = data.get("expires_at") or ""
        if exp < _now():
            await ref.delete()
            return None
        await ref.delete()
        return data.get("user_id")

    async def revoke_all_for_user(self, user_id: str) -> int:
        db = await _db()
        count = 0
        async for doc in db.collection("refresh_tokens").where("user_id", "==", user_id).stream():
            await doc.reference.delete()
            count += 1
        return count

    async def cleanup_expired(self) -> int:
        db = await _db()
        now = _now()
        count = 0
        async for doc in db.collection("refresh_tokens").stream():
            data = doc.to_dict() or {}
            if (data.get("expires_at") or "") < now:
                await doc.reference.delete()
                count += 1
        return count


class FirestoreNotificationRepository(BaseNotificationRepository):
    async def create_notification(self, notification_data: Dict[str, Any]) -> str:
        nid = notification_data.get("id") or str(uuid.uuid4())
        db = await _db()
        payload = dict(notification_data)
        payload["id"] = nid
        payload.setdefault("is_read", False)
        payload.setdefault("created_at", _now())
        await db.collection("notifications").document(nid).set(payload)
        return nid

    async def list_notifications(
        self, user_id: str, unread_only: bool = False, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        db = await _db()
        rows = []
        async for doc in db.collection("notifications").where("user_id", "==", user_id).stream():
            row = doc.to_dict() or {}
            if unread_only and row.get("is_read"):
                continue
            rows.append(row)
        rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
        return rows[offset : offset + limit]

    async def mark_read(self, notification_id: str) -> None:
        db = await _db()
        await db.collection("notifications").document(notification_id).set(
            {"is_read": True}, merge=True
        )

    async def mark_all_read(self, user_id: str) -> int:
        rows = await self.list_notifications(user_id, unread_only=True, limit=500)
        for row in rows:
            await self.mark_read(row["id"])
        return len(rows)

    async def get_unread_count(self, user_id: str) -> int:
        return len(await self.list_notifications(user_id, unread_only=True, limit=500))


class FirestoreAuditRepository(BaseAuditRepository):
    async def log_event(self, event_data: Dict[str, Any]) -> None:
        db = await _db()
        eid = str(uuid.uuid4())
        payload = dict(event_data)
        payload.setdefault("timestamp", _now())
        await db.collection("audit_logs").document(eid).set(payload)

    async def get_events(self, resource_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        db = await _db()
        rows = []
        async for doc in db.collection("audit_logs").where("resource_id", "==", resource_id).stream():
            rows.append(doc.to_dict() or {})
        rows.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
        return rows[:limit]
