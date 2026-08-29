# FAQ

Short answers. The product FAQ accordion is at `/faq`. Docs diagrams are at `/docs`.

## Try it for free

**Get started for free** creates a guest workspace. The dashboard sidebar stays pinned while you scroll.

## Missing integrations

The MCP factory builds tools in three ways: OpenAPI URL, HTTP API described in chat (no spec), or website MCP (Playwright on one origin). Details: [mcp-builder.md](mcp-builder.md).

## Own API key

Settings → Your Gemini API key, or Vault name `gemini` field `api_key`. Encrypted. Used for your runs.

## 429 quota

Shared Gemini quota can exhaust. Site health and spec-based MCP builds can still run. Chat planning needs a key or a quota reset.

## Contact mail did not arrive

`/contact` emails `godumang35@gmail.com` only when `CONTACT_SMTP_PASSWORD` is a Gmail **App Password**. Your normal Gmail password is rejected by SMTP and must never be stored. Create one at [App Passwords](https://myaccount.google.com/apppasswords) (2-Step on), paste into project-root `.env`, send again. Privacy contact: privacy@agentos.gmail.com.

## Can I put my Gmail password in `.env`?

No. Use an App Password. `.env` stays on disk and is gitignored. On Cloud Run, use Secret Manager. See [SECURITY.md](SECURITY.md).

## Google Cloud / $150 credits

Yes — Cloud Run with `min-instances 0` and secrets in Secret Manager. SQLite on Cloud Run is ephemeral; use Firestore for durable data. Guide: [deploy-gcp.md](deploy-gcp.md). This laptop does not spend your credits until you run `gcloud` while logged into that project.

## CAPTCHA on a real login site

Expected. AgentOS pauses (`WAITING_APPROVAL`). Complete the check in the opened browser, then Resume. It will not solve or skip the challenge.
