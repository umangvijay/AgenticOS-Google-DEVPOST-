"""
AgentOS — Artifact builder.

Generates a real website or small software project as files on disk from a
natural-language brief. Files are stored under data/artifacts/<user>/<id>/
and served via the artifacts API. Generated code is never executed.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.config.settings import settings
from backend.services import gemini_client

logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {
    ".html", ".css", ".js", ".json", ".md", ".txt", ".svg", ".py",
    ".ts", ".tsx", ".jsx", ".yml", ".yaml", ".toml",
}
MAX_FILES = 60
MAX_FILE_BYTES = 220_000
BATCH_SIZE = 6
SAFE_PATH = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")


class ArtifactError(Exception):
    pass


def artifacts_root() -> Path:
    base = Path(settings.SQLITE_DB_PATH).parent if settings.SQLITE_DB_PATH else Path("data")
    root = Path(base) / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_relpath(path: str) -> str:
    path = path.replace("\\", "/").lstrip("/")
    if path.startswith(".") or ".." in path.split("/"):
        raise ArtifactError(f"Illegal path: {path}")
    if not SAFE_PATH.match(path):
        raise ArtifactError(f"Illegal path: {path}")
    suffix = Path(path).suffix.lower()
    name = Path(path).name
    if name.endswith(".env.example"):
        return path
    if suffix not in ALLOWED_SUFFIXES:
        raise ArtifactError(f"Disallowed file type: {path}")
    return path


def _write_files(dest: Path, files: List[Dict[str, str]]) -> List[str]:
    written: List[str] = []
    if not files:
        raise ArtifactError("Model produced no files")
    if len(files) > MAX_FILES:
        files = files[:MAX_FILES]
    for item in files:
        rel = _safe_relpath(str(item.get("path") or ""))
        content = str(item.get("content") or "")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_FILE_BYTES:
            content = encoded[:MAX_FILE_BYTES].decode("utf-8", errors="ignore")
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(rel)
    return written


async def generate_project(
    user_id: str,
    brief: str,
    kind: str = "website",
    name: str = "",
    scale: str = "standard",
) -> Dict[str, Any]:
    """Generate a website or app as files. scale: compact | standard | full."""
    if not (brief or "").strip():
        raise ArtifactError("A brief is required")
    kind = (kind or "website").lower().strip()
    if kind not in ("website", "app"):
        kind = "website"
    scale = (scale or "standard").lower().strip()
    if scale not in ("compact", "standard", "full"):
        scale = "standard"

    size_guide = {
        "compact": "Exactly 3 files: index.html, styles.css, and script.js. One complete page.",
        "standard": "12-28 files. Multi-page site or a complete local app with components, styles, and docs.",
        "full": "24-50 files. Production-shaped project: multiple pages/modules, shared layout, README, and config.",
    }[scale]

    if scale == "compact":
        one_shot = f"""You are a production engineer. Build a compact {kind} as complete files.

PROJECT NAME: {name or "hello-agentos"}
BRIEF:
{brief[:8000]}

Return JSON only:
{{
  "name": "short-kebab-name",
  "summary": "one paragraph",
  "entrypoint": "index.html",
  "files": [
    {{"path": "index.html", "content": "full html"}},
    {{"path": "styles.css", "content": "full css"}},
    {{"path": "script.js", "content": "full js"}}
  ]
}}
Escape every quote and newline inside content strings. No markdown.
"""
        payload = await gemini_client.generate_json(one_shot)
        if not isinstance(payload, dict) or not payload.get("files"):
            payload = await gemini_client.generate_json(
                one_shot + "\n\nThe previous reply was not valid JSON with a files array. Return only the JSON object."
            )
        if not isinstance(payload, dict) or not payload.get("files"):
            raise ArtifactError("Model returned an invalid project")
        generated = [f for f in payload["files"] if isinstance(f, dict) and f.get("path")]
        plan = payload
    else:
        if kind == "website":
            extra = (
                "Produce a complete static website with real pages (not lorem-only stubs). "
                "Must include index.html plus additional pages as the brief requires (about, features, contact, etc.). "
                "Use semantic HTML, accessible markup, shared CSS, and JS only where needed. No external paid APIs."
            )
        else:
            extra = (
                "Produce a complete local software project the user can run. "
                "Include README.md with run instructions, source modules, tests if useful, and requirements.txt "
                "or package.json. Prefer Python (FastAPI) or a static+JS app. Do not include secrets."
            )

        plan_prompt = f"""You are a production engineer. Plan a {kind} project, then we will fill each file.

KIND: {kind}
SCALE: {scale} — {size_guide}
PROJECT NAME: {name or "(derive a short kebab-case name)"}
BRIEF:
{brief[:12000]}

{extra}

Return JSON only:
{{
  "name": "short-kebab-name",
  "summary": "one paragraph of architecture and what was built",
  "entrypoint": "index.html or main file",
  "files": [{{"path": "relative/path.ext", "purpose": "what this file contains"}}]
}}
Only these extensions: {", ".join(sorted(ALLOWED_SUFFIXES))}.
Every file must be necessary. Prefer a coherent multi-file structure over one giant HTML file.
"""
        plan = await gemini_client.generate_json(plan_prompt)
        if not isinstance(plan, dict) or not plan.get("files"):
            raise ArtifactError("Model returned an invalid project plan")

        planned = [f for f in plan["files"] if isinstance(f, dict) and f.get("path")][:MAX_FILES]
        generated = []

        for i in range(0, len(planned), BATCH_SIZE):
            chunk = planned[i:i + BATCH_SIZE]
            listing = "\n".join(f"- {f['path']}: {f.get('purpose', '')}" for f in chunk)
            batch_prompt = f"""Write COMPLETE file contents for this {kind} named "{plan.get('name') or name}".
Do not stub. Match the brief. Return JSON {{"files": [{{"path","content"}}]}} covering ONLY these files:

{listing}

BRIEF:
{brief[:6000]}

Only these paths. Full source in each content field.
"""
            batch = await gemini_client.generate_json(batch_prompt)
            if isinstance(batch, dict) and isinstance(batch.get("files"), list):
                generated.extend(batch["files"])
            elif isinstance(batch, list):
                generated.extend(batch)

    if not generated:
        raise ArtifactError("Model produced no files")

    artifact_id = str(uuid.uuid4())
    dest = artifacts_root() / user_id / artifact_id
    dest.mkdir(parents=True, exist_ok=True)
    written = _write_files(dest, generated)

    metadata = {
        "artifact_id": artifact_id,
        "user_id": user_id,
        "kind": kind,
        "scale": scale,
        "name": plan.get("name") or name or kind,
        "summary": plan.get("summary") or "",
        "entrypoint": plan.get("entrypoint") or (written[0] if written else ""),
        "files": written,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (dest / "artifact.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Generated %s/%s artifact %s (%d files) for user %s", kind, scale, artifact_id, len(written), user_id)
    return metadata


def list_artifacts(user_id: str) -> List[Dict[str, Any]]:
    folder = artifacts_root() / user_id
    if not folder.exists():
        return []
    items = []
    for child in sorted(folder.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        meta = child / "artifact.json"
        if meta.is_file():
            try:
                items.append(json.loads(meta.read_text(encoding="utf-8")))
            except Exception:
                continue
    return items


def load_artifact(user_id: str, artifact_id: str) -> Dict[str, Any]:
    meta = artifacts_root() / user_id / artifact_id / "artifact.json"
    if not meta.is_file():
        raise ArtifactError("Artifact not found")
    return json.loads(meta.read_text(encoding="utf-8"))


def read_artifact_file(user_id: str, artifact_id: str, relpath: str) -> Path:
    rel = _safe_relpath(relpath)
    path = artifacts_root() / user_id / artifact_id / rel
    if not path.is_file():
        raise ArtifactError("File not found")
    # Stay inside the artifact directory
    path.resolve().relative_to((artifacts_root() / user_id / artifact_id).resolve())
    return path
