# Contact SMTP

```mermaid
flowchart LR
  form[Contact form] --> next[Next /api/contact]
  next --> api[FastAPI /api/v1/contact]
  api --> inbox[contact_inbox.json]
  api --> smtp[Gmail STARTTLS]
  smtp --> team[godumang35@gmail.com]
```

Requires `CONTACT_SMTP_USERNAME` and a **Gmail App Password** in `CONTACT_SMTP_PASSWORD` (never the mailbox password). `.env` is gitignored. Cloud Run uses Secret Manager. FormSubmit is not used from localhost. Status: `GET /api/v1/contact/status` (`smtp_configured`, no secret).
