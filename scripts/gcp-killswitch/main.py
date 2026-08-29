# Disable billing at $100 — AgentOS kill switch

Cloud Function (2nd gen) triggered by a Billing budget Pub/Sub message.
When reported **gross** usage reaches `KILL_AT_USD` (default 100), it:

1. Sets Cloud Run services `agentos-api` and `agentos-frontend` to max instances 0
2. Unlinks the project from its billing account (stops Vertex, Cloud Run, Firestore, …)

Google does **not** offer a hard cap. Budget notifications can lag hours (sometimes longer).
A $100 kill on a $150 grant leaves headroom for that lag. See
https://cloud.google.com/billing/docs/how-to/disable-billing-with-notifications

Set `SIMULATE_DEACTIVATION=true` for a dry run. Production deploy uses `false`.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

from cloudevents.http.event import CloudEvent
import functions_framework
from google.api_core import exceptions
from google.auth import default
from google.auth.transport.requests import Request
from google.cloud import billing_v1

billing_client = billing_v1.CloudBillingClient()

RUN_SERVICES = (
    os.getenv("KILL_RUN_SERVICES") or "agentos-api,agentos-frontend"
).split(",")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def get_project_id() -> str:
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if project_id:
        return project_id
    url = "http://metadata.google.internal/computeMetadata/v1/project/project-id"
    req = urllib.request.Request(url, headers={"Metadata-Flavor": "Google"})
    return urllib.request.urlopen(req, timeout=5).read().decode()


def _payload(cloud_event: CloudEvent) -> dict:
    raw = cloud_event.data.get("message", {}).get("data") or ""
    if not raw:
        return {}
    decoded = base64.b64decode(raw).decode("utf-8")
    return json.loads(decoded)


def _scale_run_to_zero(project_id: str, region: str, simulate: bool) -> None:
    creds, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    token = creds.token
    for name in (s.strip() for s in RUN_SERVICES if s.strip()):
        url = (
            f"https://run.googleapis.com/v2/projects/{project_id}"
            f"/locations/{region}/services/{name}"
            "?updateMask=template.scaling.max_instance_count"
        )
        body = json.dumps({"template": {"scaling": {"maxInstanceCount": 0}}}).encode()
        print(f"Cloud Run max instances → 0: {name} simulate={simulate}")
        if simulate:
            continue
        req = urllib.request.Request(
            url,
            data=body,
            method="PATCH",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                print(f"Cloud Run {name}: HTTP {resp.status}")
        except urllib.error.HTTPError as exc:
            # Service may not exist yet; still disable billing.
            print(f"Cloud Run {name} scale skipped: HTTP {exc.code}")


def _is_billing_enabled(project_name: str) -> bool:
    try:
        info = billing_client.get_project_billing_info(name=project_name)
        return bool(info.billing_enabled)
    except Exception as exc:
        print(f"Could not read billing info ({exc}); assuming enabled")
        return True


def _disable_billing(project_name: str, simulate: bool) -> None:
    if simulate:
        print(f"SIMULATE: would unlink billing for {project_name}")
        return
    billing_client.update_project_billing_info(
        name=project_name,
        project_billing_info=billing_v1.ProjectBillingInfo(billing_account_name=""),
    )
    print(f"Billing unlinked for {project_name}")


@functions_framework.cloud_event
def stop_billing(cloud_event: CloudEvent) -> None:
    simulate = _env_bool("SIMULATE_DEACTIVATION", False)
    kill_at = float(os.getenv("KILL_AT_USD") or "100")
    region = os.getenv("GOOGLE_CLOUD_REGION") or "us-central1"
    project_id = get_project_id()
    project_name = f"projects/{project_id}"

    event = _payload(cloud_event)
    cost = float(event.get("costAmount") or 0)
    budget = float(event.get("budgetAmount") or 0)
    print(
        f"Budget notice cost={cost} budget={budget} kill_at={kill_at} "
        f"simulate={simulate} project={project_id}"
    )

    if cost < kill_at:
        print(f"Within cap ({cost} < {kill_at}) — no kill.")
        return

    print(f"Kill switch: usage ${cost} >= ${kill_at}")
    _scale_run_to_zero(project_id, region, simulate)

    if not _is_billing_enabled(project_name):
        print("Billing already disabled.")
        return
    try:
        _disable_billing(project_name, simulate)
    except exceptions.PermissionDenied:
        print(
            "Permission denied unlinking billing. Grant the function SA "
            "roles/billing.projectManager (or billing.admin) on the BILLING ACCOUNT."
        )
        raise
