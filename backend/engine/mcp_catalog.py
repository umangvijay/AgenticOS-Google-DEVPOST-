"""Named MCP catalogs so builds do not depend on Gemini or JSONPlaceholder."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

JSONPLACEHOLDER_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "JSONPlaceholder", "version": "1.0.0"},
    "servers": [{"url": "https://jsonplaceholder.typicode.com"}],
    "paths": {
        "/posts": {
            "get": {
                "operationId": "listPosts",
                "summary": "List posts",
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/posts/{id}": {
            "get": {
                "operationId": "getPost",
                "summary": "Get a post",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/users": {
            "get": {
                "operationId": "listUsers",
                "summary": "List users",
                "responses": {"200": {"description": "ok"}},
            }
        },
    },
}

STRIPE_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Stripe",
        "version": "2024-06-20",
        "description": "Stripe Payments API subset. Store the secret key in Vault.",
    },
    "servers": [{"url": "https://api.stripe.com"}],
    "paths": {
        "/v1/balance": {
            "get": {
                "operationId": "getBalance",
                "summary": "Retrieve account balance",
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/v1/customers": {
            "get": {
                "operationId": "listCustomers",
                "summary": "List customers",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "ok"}},
            },
            "post": {
                "operationId": "createCustomer",
                "summary": "Create a customer",
                "requestBody": {
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string"},
                                    "name": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "ok"}},
            },
        },
        "/v1/customers/{id}": {
            "get": {
                "operationId": "getCustomer",
                "summary": "Retrieve a customer",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/v1/charges": {
            "get": {
                "operationId": "listCharges",
                "summary": "List charges",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/v1/payment_intents": {
            "get": {
                "operationId": "listPaymentIntents",
                "summary": "List payment intents",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "ok"}},
            },
            "post": {
                "operationId": "createPaymentIntent",
                "summary": "Create a payment intent",
                "requestBody": {
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "type": "object",
                                "required": ["amount", "currency"],
                                "properties": {
                                    "amount": {"type": "integer"},
                                    "currency": {"type": "string"},
                                    "customer": {"type": "string"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "ok"}},
            },
        },
    },
}

GMAIL_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Gmail",
        "version": "v1",
        "description": "Gmail API subset. Authenticate with a Google OAuth access token in Vault.",
    },
    "servers": [{"url": "https://gmail.googleapis.com"}],
    "paths": {
        "/gmail/v1/users/me/profile": {
            "get": {
                "operationId": "getProfile",
                "summary": "Get the Gmail profile for the signed-in user",
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/gmail/v1/users/me/labels": {
            "get": {
                "operationId": "listLabels",
                "summary": "List Gmail labels",
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/gmail/v1/users/me/messages": {
            "get": {
                "operationId": "listMessages",
                "summary": "List messages",
                "parameters": [
                    {"name": "q", "in": "query", "schema": {"type": "string"}},
                    {"name": "maxResults", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/gmail/v1/users/me/messages/{id}": {
            "get": {
                "operationId": "getMessage",
                "summary": "Get a message",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "ok"}},
            }
        },
        "/gmail/v1/users/me/messages/send": {
            "post": {
                "operationId": "sendMessage",
                "summary": "Send a message (raw RFC 2822, base64url)",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["raw"],
                                "properties": {"raw": {"type": "string"}},
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "ok"}},
            }
        },
    },
}

PETSTORE_OPENAPI = "https://petstore3.swagger.io/api/v3/openapi.json"

# (canonical_id, display_name, spec_or_url, method, auth_type, aliases)
_APPS: List[tuple] = [
    ("stripe", "Stripe", STRIPE_SPEC, "spec", "API_KEY", (
        "stripe", "strip", "strype", "strpe", "stripes",
    )),
    ("gmail", "Gmail", GMAIL_SPEC, "spec", "OAUTH2", (
        "gmail", "g-mail", "google mail", "googlemail", "g mail",
    )),
    ("jsonplaceholder", "JSONPlaceholder", JSONPLACEHOLDER_SPEC, "spec", "NONE", (
        "jsonplaceholder", "json placeholder", "placeholder",
    )),
    ("petstore", "Petstore", PETSTORE_OPENAPI, "url", "NONE", ("petstore",)),
]


def detect_named_apps(text: str) -> List[str]:
    lowered = (text or "").lower()
    found: List[str] = []
    for app_id, _name, _spec, _method, _auth, aliases in _APPS:
        for alias in aliases:
            if " " in alias:
                if alias in lowered:
                    found.append(app_id)
                    break
            elif re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered):
                found.append(app_id)
                break
    # Preserve order, unique
    out: List[str] = []
    for app_id in found:
        if app_id not in out:
            out.append(app_id)
    return out


def build_input_for_app(app_id: str) -> Optional[Dict[str, str]]:
    for cid, name, spec, method, auth, _aliases in _APPS:
        if cid != app_id:
            continue
        source = spec if isinstance(spec, str) else json.dumps(spec)
        return {"method": method, "source": source, "name": name, "auth_type": auth}
    return None


def resolve_named_spec(text: str) -> Optional[Tuple[str, str, str]]:
    """Return (spec_json_or_url, display_name, auth_type) for the first named app."""
    apps = detect_named_apps(text)
    if not apps:
        return None
    payload = build_input_for_app(apps[0])
    if not payload:
        return None
    return payload["source"], payload["name"], payload["auth_type"]


# Public API hosts inferred from words in the user's request. Used only when Gemini
# cannot emit OpenAPI. This is not a canned reply — operations still come from the prompt.
_HOST_HINTS: Tuple[Tuple[str, str, str], ...] = (
    ("github", "https://api.github.com", "GitHub"),
    ("gitlab", "https://gitlab.com/api/v4", "GitLab"),
    ("bitbucket", "https://api.bitbucket.org/2.0", "Bitbucket"),
    ("slack", "https://slack.com/api", "Slack"),
    ("discord", "https://discord.com/api/v10", "Discord"),
    ("notion", "https://api.notion.com", "Notion"),
    ("linear", "https://api.linear.app", "Linear"),
    ("asana", "https://app.asana.com/api/1.0", "Asana"),
    ("trello", "https://api.trello.com/1", "Trello"),
    ("airtable", "https://api.airtable.com", "Airtable"),
    ("hubspot", "https://api.hubapi.com", "HubSpot"),
    ("shopify", "https://admin.shopify.com", "Shopify"),
    ("twilio", "https://api.twilio.com", "Twilio"),
    ("sendgrid", "https://api.sendgrid.com", "SendGrid"),
    ("dropbox", "https://api.dropboxapi.com", "Dropbox"),
    ("zoom", "https://api.zoom.us/v2", "Zoom"),
    ("pokeapi", "https://pokeapi.co/api/v2", "PokeAPI"),
    ("pokemon", "https://pokeapi.co/api/v2", "PokeAPI"),
    ("open-meteo", "https://api.open-meteo.com/v1", "Open-Meteo"),
    ("openmeteo", "https://api.open-meteo.com/v1", "Open-Meteo"),
    ("httpbin", "https://httpbin.org", "HTTPBin"),
    ("datadog", "https://api.datadoghq.com", "Datadog"),
    ("sentry", "https://sentry.io/api/0", "Sentry"),
    ("okta", "https://okta.com", "Okta"),
    ("supabase", "https://api.supabase.com", "Supabase"),
    ("vercel", "https://api.vercel.com", "Vercel"),
    ("cloudflare", "https://api.cloudflare.com/client/v4", "Cloudflare"),
    ("figma", "https://api.figma.com", "Figma"),
    ("spotify", "https://api.spotify.com/v1", "Spotify"),
    ("reddit", "https://oauth.reddit.com", "Reddit"),
    ("youtube", "https://www.googleapis.com/youtube/v3", "YouTube"),
)

_PATH_ALIASES = {
    "https://api.github.com": {
        "repo": "/user/repos",
        "repos": "/user/repos",
        "repositories": "/user/repos",
        "issue": "/issues",
        "issues": "/issues",
        "pull": "/repos/{owner}/{repo}/pulls",
        "pulls": "/repos/{owner}/{repo}/pulls",
        "pr": "/repos/{owner}/{repo}/pulls",
        "user": "/user",
        "gist": "/gists",
        "gists": "/gists",
        "event": "/events",
        "events": "/events",
        "zen": "/zen",
    },
    "https://pokeapi.co/api/v2": {
        "pokemon": "/pokemon",
        "ability": "/ability",
        "type": "/type",
        "berry": "/berry",
    },
    "https://api.open-meteo.com/v1": {
        "weather": "/forecast",
        "forecast": "/forecast",
    },
}

_STOP_NOUNS = frozenset({
    "the", "and", "for", "mcp", "tool", "tools", "create", "build", "make", "generate",
    "an", "api", "rest", "http", "https", "with", "that", "this", "from", "your", "any",
    "please", "then", "also", "send", "write", "email", "openapi", "swagger", "spec",
    "integration", "connector", "so", "can", "list", "get", "fetch", "public",
})


def _server_from_prompt(text: str) -> Optional[Tuple[str, str]]:
    for match in re.finditer(r"https://[^\s\"'<>]+", text or ""):
        raw = match.group(0).rstrip(").,;]")
        parsed = urlparse(raw)
        host = (parsed.netloc or "").lower()
        if not host or host in ("localhost", "127.0.0.1"):
            continue
        if host in ("github.com", "www.github.com"):
            return "https://api.github.com", "GitHub"
        origin = f"{parsed.scheme}://{parsed.netloc}"
        path = (parsed.path or "").rstrip("/")
        if path and any(p in path.lower() for p in ("/api", "/v1", "/v2", "/v3", "/rest")):
            return origin + path, parsed.netloc.split(".")[0].title()
        if host.startswith("api.") or "googleapis.com" in host:
            return origin, parsed.netloc.split(".")[0].title()
        return origin, parsed.netloc.split(".")[0].title()
    lowered = (text or "").lower()
    for token, url, title in _HOST_HINTS:
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered):
            return url, title
    named = detect_named_apps(text or "")
    if named:
        payload = build_input_for_app(named[0])
        if payload and payload.get("method") == "spec":
            try:
                spec = json.loads(payload["source"])
                servers = spec.get("servers") or []
                if servers:
                    return servers[0]["url"], payload["name"]
            except Exception:
                pass
    return None


def _resources_from_prompt(text: str) -> List[str]:
    found: List[str] = []
    lowered = (text or "").lower()
    for match in re.finditer(
        r"\b(?:list|get|fetch|read|create|post|update|delete|send|search|write)\s+"
        r"((?:(?:my|a|an|the|public)\s+)*[a-z][a-z0-9_-]{1,32}"
        r"(?:\s+and\s+(?:(?:my|a|an|the|public)\s+)*[a-z][a-z0-9_-]{1,32})*)",
        lowered,
    ):
        chunk = match.group(1)
        for part in re.split(r"\s+and\s+", chunk):
            noun = re.sub(r"^(?:my|a|an|the|public)\s+", "", part).strip()
            noun = noun.split()[-1] if noun else ""
            if noun in _STOP_NOUNS or noun in found:
                continue
            found.append(noun)
    return found[:8]


def _wants_write(text: str) -> bool:
    cleaned = re.sub(
        r"\b(?:create|build|make|generate)\s+(?:an?\s+)?(?:mcp|tool|tools|integration)s?\b",
        " ",
        (text or "").lower(),
    )
    return bool(re.search(r"\b(?:create|post|send|update|delete|write)\s+(?!mcp\b|tool\b)", cleaned))


def _operation(
    method: str,
    op_id: str,
    summary: str,
    path_params: Optional[List[str]] = None,
    query_params: Optional[List[dict]] = None,
) -> dict:
    op: Dict[str, object] = {
        "operationId": op_id,
        "summary": summary,
        "responses": {"200": {"description": "ok"}},
    }
    params: List[dict] = []
    if path_params:
        params.extend(
            {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
            for name in path_params
        )
    if query_params:
        params.extend(query_params)
    if params:
        op["parameters"] = params
    if method == "post":
        op["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": {"type": "object", "additionalProperties": True},
                }
            }
        }
    return op


def sketch_openapi_from_prompt(source: str) -> Optional[str]:
    """Build a small OpenAPI 3 spec from the user's words when the model cannot."""
    text = (source or "").strip()
    if not text:
        return None
    inferred = _server_from_prompt(text)
    if not inferred:
        return None
    server, title = inferred
    resources = _resources_from_prompt(text)
    aliases = _PATH_ALIASES.get(server.rstrip("/"), {})
    wants_write = _wants_write(text)
    paths: Dict[str, dict] = {}

    query_for = {
        "https://api.open-meteo.com/v1": {
            "/forecast": [
                {"name": "latitude", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "longitude", "in": "query", "required": True, "schema": {"type": "number"}},
                {"name": "current_weather", "in": "query", "schema": {"type": "boolean"}},
            ]
        }
    }

    def add_path(path: str, method: str, op_id: str, summary: str) -> None:
        params = re.findall(r"\{([^}]+)\}", path)
        qparams = (query_for.get(server.rstrip("/")) or {}).get(path)
        paths.setdefault(path, {})[method] = _operation(
            method, op_id, summary, params or None, qparams
        )

    if server.rstrip("/") == "https://api.github.com" and not resources:
        resources = ["events"] if "event" in text.lower() else ["repos", "issues"]
    if server.rstrip("/") == "https://pokeapi.co/api/v2" and not resources:
        resources = ["pokemon"]
    if server.rstrip("/") == "https://api.open-meteo.com/v1" and not resources:
        resources = ["forecast"]

    for noun in resources:
        path = aliases.get(noun) or aliases.get(noun.rstrip("s")) or f"/{noun}"
        add_path(path, "get", f"list_{noun}", f"List {noun}")
        skip_item = "{" in path or path.rstrip("/") in ("/events", "/zen", "/forecast")
        if not skip_item:
            item = f"{path.rstrip('/')}/{{id}}"
            add_path(item, "get", f"get_{noun}", f"Get {noun} by id")
            if wants_write:
                add_path(path, "post", f"create_{noun}", f"Create {noun}")
        elif wants_write and "get" in paths.get(path, {}):
            add_path(path, "post", f"create_{noun}", f"Create {noun}")

    if not paths:
        add_path("/", "get", "getRoot", f"Call {title}")

    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": "1.0.0",
            "description": f"Sketched from the user's request for {title}.",
        },
        "servers": [{"url": server}],
        "paths": paths,
    }
    return json.dumps(spec)


_STOP_SCORE = frozenset({
    "the", "and", "for", "with", "that", "this", "from", "your", "please",
    "then", "also", "mcp", "tool", "tools", "create", "build", "make", "can",
    "list", "get", "fetch", "http", "https", "open", "home", "site",
})


def pick_catalog_tool(goal: str, catalog: Sequence[Any]) -> Optional[Dict[str, Any]]:
    """Choose the catalog tool that best matches a follow-up chat goal."""
    if not catalog:
        return None
    lowered = (goal or "").lower()
    words = [w for w in re.findall(r"[a-z][a-z0-9_-]{2,}", lowered) if w not in _STOP_SCORE]
    best: Optional[Dict[str, Any]] = None
    best_score = -1
    for raw in catalog:
        tool = raw if isinstance(raw, dict) else {}
        name = str(tool.get("name") or "")
        mcp = str(tool.get("mcp_name") or "")
        desc = str(tool.get("description") or "")
        hay = f"{name} {mcp} {desc}".lower()
        score = 0
        for word in words:
            if word in hay:
                score += 2
        nl = name.lower()
        if "login" in lowered and "login" in nl:
            score += 8
        if "runonsite" in nl and any(w in lowered for w in ("browse", "on the site", "runonsite", "use run")):
            score += 6
        if "openhome" in nl and "home" in lowered:
            score += 6
        if any(w in lowered for w in ("pokemon", "pokeapi")) and "poke" in hay:
            score += 8
        if "github" in lowered and "github" in hay:
            score += 8
        if "event" in lowered and "event" in nl:
            score += 6
        if "weather" in lowered or "forecast" in lowered:
            if "forecast" in hay or "meteo" in hay:
                score += 8
        if score > best_score:
            best_score = score
            best = tool
    if best_score <= 0:
        return catalog[0] if isinstance(catalog[0], dict) else None
    return best


def arguments_for_catalog_tool(tool: Dict[str, Any], goal: str) -> Dict[str, Any]:
    """Fill safe arguments for a catalog tool from the user's follow-up text."""
    schema = tool.get("input_schema") or {}
    props = schema.get("properties") or {}
    required = list(schema.get("required") or [])
    args: Dict[str, Any] = {}
    lowered = (goal or "").lower()
    cred = None
    m = re.search(
        r"(?:vault\s+credential|credential(?:_name)?|named)\s+[\"']?([a-zA-Z0-9._-]{1,64})",
        goal or "",
        re.I,
    )
    if m:
        cred = m.group(1)
    if cred and ("credential_name" in props or "credential_name" in required):
        args["credential_name"] = cred
    name = str(tool.get("name") or "").lower()
    if "goal" in props and name in ("runonsite", "run_on_site"):
        args["goal"] = goal
    if "latitude" in props and "longitude" in props:
        if "london" in lowered:
            args.setdefault("latitude", 51.51)
            args.setdefault("longitude", -0.13)
        elif "new york" in lowered or "nyc" in lowered:
            args.setdefault("latitude", 40.71)
            args.setdefault("longitude", -74.01)
        else:
            args.setdefault("latitude", 52.52)
            args.setdefault("longitude", 13.41)
        if "current_weather" in props:
            args.setdefault("current_weather", True)
    return args
