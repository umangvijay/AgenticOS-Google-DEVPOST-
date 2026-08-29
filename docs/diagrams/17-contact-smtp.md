# Contact SMTP

```mermaid
flowchart LR
  form[ContactForm] --> next[Next_api_contact]
  next --> api[FastAPI_contact]
  api --> inbox[contact_inbox.json]
  api --> smtp[Gmail_STARTTLS]
  smtp --> team[godumang35]
```

Requires `CONTACT_SMTP_USERNAME` and a Gmail App Password in `CONTACT_SMTP_PASSWORD`. FormSubmit is not used from localhost.
