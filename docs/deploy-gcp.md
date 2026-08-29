# Deploy AgentOS on Google Cloud

Laptop default stays SQLite. GCP is optional hosting. A new-account **$150 credit** is enough for a **Cloud Run demo** if you scale to zero and do not leave a worker at `min_instances = 1`.

This repo’s Terraform (`terraform/environments/dev`) can provision IAM, Artifact Registry, Secret Manager, Firestore, Pub/Sub, and two Cloud Run services. Python does **not** currently read `SERVICE_TYPE`. The FastAPI process already runs the workflow engine in-process. For credits, **deploy the API (and frontend) first**; treat the Terraform worker as optional later.

## What must never go in the image

- `.env`
- Gmail **login** password (use an [App Password](https://myaccount.google.com/apppasswords) only)
- `GEMINI_API_KEY`, `SECRETS_MASTER_KEY`, JWT PEMs as build args

Use [Secret Manager](https://cloud.google.com/secret-manager/docs). Cloud Run mounts them as environment variables at runtime.

## Prerequisites

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud billing accounts list   # attach billing so the $150 grant applies
```

Enable APIs:

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com
```

Create secrets (values stay in your shell history — prefer `gcloud secrets versions add --data-file=-`):

```bash
echo -n 'YOUR_GEMINI_KEY' | gcloud secrets create gemini-api-key --data-file=-
echo -n 'YOUR_16_CHAR_APP_PASSWORD' | gcloud secrets create contact-smtp-password --data-file=-
echo -n 'LONG_RANDOM_VAULT_MASTER' | gcloud secrets create secrets-master-key --data-file=-
```

## Cheap path: one Cloud Run API (recommended for credits)

From the repo root, after `gcloud` is on the right project:

```bash
gcloud run deploy agentos-api \
  --source . \
  --dockerfile Dockerfile.api \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 4 \
  --timeout 300 \
  --set-env-vars STORAGE_BACKEND=sqlite,APP_ENV=production,CONTACT_TO_EMAIL=godumang35@gmail.com,CONTACT_SMTP_HOST=smtp.gmail.com,CONTACT_SMTP_PORT=587,CONTACT_SMTP_USERNAME=godumang35@gmail.com \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,CONTACT_SMTP_PASSWORD=contact-smtp-password:latest,SECRETS_MASTER_KEY=secrets-master-key:latest
```

`--source .` uses Cloud Build. `.dockerignore` already excludes `.env`.

**SQLite on Cloud Run is ephemeral.** When the instance scales to zero, `data/agentos.db` is gone. Fine for a live demo. For a durable contest deploy, set `STORAGE_BACKEND=firestore` and create a Firestore database in Native mode first.

Frontend: set `API_BASE_URL` / `NEXT_PUBLIC_API_URL` to the Cloud Run API URL, then deploy `frontend/` with `frontend/Dockerfile.frontend` (Next.js `output: "standalone"`). Update `CORS_ALLOWED_ORIGINS` on the API to that frontend origin.

Playwright in `Dockerfile.api` installs Chromium. Website MCP and headed HITL work poorly on Cloud Run (no display). Website MCP for a public Cloud demo should use headless probes on CAPTCHA-free sites, or keep browser flows on a laptop.

## Full Terraform path

`terraform/environments/dev` expects a GCS state bucket `agenticos-tfstate-dev` and image URLs for API/worker.

1. Create the state bucket once.
2. Add secret versions for `agenticos-gemini_api_key`, `agenticos-contact_smtp_password`, `agenticos-secrets_master_key` (see `terraform/modules/secrets`).
3. Set `min_instances = 0` on every Cloud Run module (API already is; worker must stay 0 or it bills all day).
4. `STORAGE_BACKEND=firestore` in shared env.
5. `terraform -chdir=terraform/environments/dev init && terraform apply`

`cloudbuild.yaml` builds `Dockerfile.api` and `Dockerfile.worker` (same image today) and deploys `agenticos-api` / `agenticos-worker`.

## Credits hygiene

- Prefer `min-instances 0`.
- Do not enable unused APIs.
- Delete the Cloud Run services after the demo if you are not iterating.
- Vertex/Gemini usage is separate from Cloud Run CPU; a busy planner can spend more than hosting.

## What this document does not do

It does not spend your $150 from this machine. You must be logged into the project that owns the grant, then run the commands above.
