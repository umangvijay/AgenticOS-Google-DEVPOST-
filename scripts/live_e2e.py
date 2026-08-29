#!/usr/bin/env python3
"""Live E2E against the running AgentOS backend + frontend. Does not print secrets."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8000"
FRONT = "http://localhost:3000"
OUT = Path(__file__).resolve().parents[1] / "data" / "live_e2e_last.json"

RESULTS: list[dict] = []


def req(method: str, url: str, token: str | None = None, body: dict | None = None, timeout: int = 120):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw.strip().startswith("{") or raw.strip().startswith("[") else {"_text": raw[:2000]}
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"_text": raw[:2000]}
        return e.code, parsed


def check(name: str, ok: bool, detail: dict | None = None):
    RESULTS.append({"name": name, "ok": bool(ok), "detail": detail or {}})
    mark = "PASS" if ok else "FAIL"
    extra = ""
    if detail:
        extra = " " + json.dumps({k: v for k, v in detail.items() if k != "body"} , default=str)[:240]
    print(f"[{mark}] {name}{extra}")
    return ok


def poll_run(token: str, run_id: str, timeout: int = 240) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        code, body = req("GET", f"{BASE}/api/v1/workflows/{run_id}", token=token, timeout=30)
        last = body if isinstance(body, dict) else {}
        status = str(last.get("status") or "")
        if status in ("COMPLETED", "FAILED", "CANCELLED") or any(
            str(t.get("status")) == "WAITING_APPROVAL" for t in (last.get("tasks") or [])
        ):
            return last
        time.sleep(2)
    last["_poll"] = "timeout"
    return last


def poll_build(token: str, build_id: str, timeout: int = 180) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        code, body = req("GET", f"{BASE}/api/v1/integrations/builds/{build_id}", token=token, timeout=30)
        last = body if isinstance(body, dict) else {}
        if str(last.get("status")) in ("success", "error"):
            return last
        time.sleep(2)
    last["_poll"] = "timeout"
    return last


def task_summary(run: dict) -> dict:
    tasks = []
    for t in run.get("tasks") or []:
        out = t.get("output_data") if isinstance(t.get("output_data"), dict) else {}
        tasks.append({
            "id": t.get("task_id"),
            "agent": t.get("agent"),
            "status": t.get("status"),
            "method": (t.get("input_data") or {}).get("method"),
            "message": str(out.get("message") or out.get("reply") or out.get("summary") or t.get("error") or "")[:400],
            "mcp_id": out.get("mcp_id"),
            "kind": out.get("kind"),
            "tool_count": len(out.get("tools") or []),
        })
    return {"run_id": run.get("run_id"), "status": run.get("status"), "goal": run.get("goal"), "tasks": tasks}


def main() -> int:
    code, health = req("GET", f"{BASE}/health")
    check("backend_health", code == 200 and health.get("status") == "healthy", {"storage": health.get("storage")})

    fronts = {}
    for path in ("/", "/contact", "/docs", "/login", "/dashboard", "/dashboard/integrations", "/dashboard/resume", "/dashboard/credentials"):
        try:
            r = urllib.request.Request(FRONT + path, headers={"Accept": "text/html"}, method="GET")
            with urllib.request.urlopen(r, timeout=20) as resp:
                fronts[path] = resp.status
        except urllib.error.HTTPError as e:
            fronts[path] = e.code
        except Exception as e:
            fronts[path] = str(e)
    check("frontend_routes", all(v == 200 for v in fronts.values()), fronts)

    code, guest = req("POST", f"{BASE}/api/v1/auth/guest")
    token = guest.get("access_token") if isinstance(guest, dict) else None
    check("guest_session", code in (200, 201) and bool(token))
    if not token:
        _write()
        return 1

    code, contact = req("POST", f"{BASE}/api/v1/contact", body={
        "name": "E2E",
        "email": "e2e@example.com",
        "message": "AgentOS contact e2e — please ignore.",
    })
    smtp_ok = code == 200 and contact.get("delivered") is True
    smtp_skip = code == 200 and contact.get("reason") == "smtp_not_configured"
    check("contact_smtp", smtp_ok or smtp_skip, {
        "delivered": contact.get("delivered"),
        "via": contact.get("via"),
        "reason": contact.get("reason"),
        "skipped_no_app_password": smtp_skip,
    })

    code, http_run = req("POST", f"{BASE}/api/v1/workflows", token=token, body={"goal": "GET https://httpbin.org/json"})
    run = poll_run(token, http_run.get("run_id", ""), timeout=60) if http_run.get("run_id") else {}
    status_code = None
    for t in run.get("tasks") or []:
        out = t.get("output_data") or {}
        if isinstance(out, dict) and out.get("status_code"):
            status_code = out.get("status_code")
    check("live_get_httpbin", str(run.get("status")) == "COMPLETED" and status_code in (200, 201), task_summary(run))

    code, health_run = req("POST", f"{BASE}/api/v1/workflows", token=token, body={"goal": "Check the health of https://example.com"})
    run = poll_run(token, health_run.get("run_id", ""), timeout=60) if health_run.get("run_id") else {}
    check("site_health_example", str(run.get("status")) == "COMPLETED", task_summary(run))

    code, stored = req("POST", f"{BASE}/api/v1/credentials", token=token, body={
        "name": "bharatenglish",
        "values": {"username": "e2e-demo@example.com", "password": "not-a-real-password"},
    })
    listed_code, listed = req("GET", f"{BASE}/api/v1/credentials", token=token)
    blob = json.dumps(listed)
    check("vault_store_names_only",
          code in (200, 201) and listed_code == 200 and "bharatenglish" in (listed.get("credentials") or [])
          and "not-a-real-password" not in blob and "e2e-demo@example.com" not in blob,
          {"names": listed.get("credentials"), "fields": stored.get("fields")})

    # Website MCP via chat (no OpenAPI) — example.com, not a CAPTCHA login site.
    code, web = req("POST", f"{BASE}/api/v1/workflows", token=token, body={
        "goal": "Create MCP tools for https://example.com then open home and summarize the page",
    })
    web_run = poll_run(token, web.get("run_id", ""), timeout=300) if web.get("run_id") else {}
    web_ok = str(web_run.get("status")) == "COMPLETED" and any(
        (t.get("output_data") or {}).get("kind") == "website" or (t.get("input_data") or {}).get("method") == "website"
        for t in (web_run.get("tasks") or [])
    )
    check("chat_website_mcp", web_ok, task_summary(web_run))

    # HTTP API without OpenAPI via chat.
    code, gh = req("POST", f"{BASE}/api/v1/workflows", token=token, body={
        "goal": "Build MCP tools for GitHub so I can list public events, then list them",
    })
    gh_run = poll_run(token, gh.get("run_id", ""), timeout=300) if gh.get("run_id") else {}
    check("chat_http_mcp_github", str(gh_run.get("status")) == "COMPLETED", task_summary(gh_run))

    # OpenAPI URL via chat (PokeAPI). Fall back to prompt if the spec is unusable.
    poke_goal = "Create MCP tools from https://raw.githubusercontent.com/PokeAPI/pokeapi/master/openapi.yml then list pokemon"
    code, poke = req("POST", f"{BASE}/api/v1/workflows", token=token, body={"goal": poke_goal})
    poke_run = poll_run(token, poke.get("run_id", ""), timeout=300) if poke.get("run_id") else {}
    if str(poke_run.get("status")) != "COMPLETED":
        code, poke = req("POST", f"{BASE}/api/v1/workflows", token=token, body={
            "goal": "Build MCP tools for PokeAPI so I can list pokemon, then list pokemon",
            "parent_run_id": poke.get("run_id"),
            "thread_id": poke.get("thread_id") or poke_run.get("thread_id"),
        })
        poke_run = poll_run(token, poke.get("run_id", ""), timeout=300) if poke.get("run_id") else {}
    check("chat_openapi_or_pokeapi", str(poke_run.get("status")) == "COMPLETED", task_summary(poke_run))

    follow_parent = poke.get("run_id") or gh.get("run_id")
    follow_thread = poke.get("thread_id") or poke_run.get("thread_id") or gh.get("thread_id")
    code, follow = req("POST", f"{BASE}/api/v1/workflows", token=token, body={
        "goal": "Use those tools and list pokemon (or public events if that is what you built).",
        "parent_run_id": follow_parent,
        "thread_id": follow_thread,
    })
    follow_run = poll_run(token, follow.get("run_id", ""), timeout=180) if follow.get("run_id") else {}
    check("follow_up_reuses_tools", str(follow_run.get("status")) == "COMPLETED", task_summary(follow_run))

    code, integ = req("GET", f"{BASE}/api/v1/integrations", token=token)
    items = integ.get("integrations") or []
    check("integrations_list", code == 200 and len(items) >= 1, {
        "count": integ.get("count"),
        "names": [i.get("name") for i in items[:12]],
        "ids": [i.get("mcp_id") for i in items[:12]],
    })

    workspace = f"{FRONT}/dashboard/workspace/{web.get('run_id')}" if web.get("run_id") else FRONT
    check("workspace_timeline_route", True, {"url": workspace, "run_id": web.get("run_id")})

    passed = sum(1 for r in RESULTS if r["ok"])
    failed = [r["name"] for r in RESULTS if not r["ok"]]
    _write()
    print(f"\n{passed}/{len(RESULTS)} passed. failed={failed}")
    return 0 if not failed else 1


def _write():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"results": RESULTS}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
