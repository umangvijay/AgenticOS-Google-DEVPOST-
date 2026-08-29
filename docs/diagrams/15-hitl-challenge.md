# HITL for CAPTCHA, OTP, and MFA

AgentOS does not solve these. It pauses.

```mermaid
flowchart TD
  browse[PlaywrightSnapshot] --> detect{Challenge}
  detect -->|no| act[ClickTypeNavigate]
  detect -->|captcha otp mfa| headed[OpenHeadedBrowser]
  headed --> pause[WAITING_APPROVAL]
  pause --> user[UserCompletesCheck]
  user --> resume[POST resume]
  resume --> continue[ContinueSameSession]
```

Workspace shows a banner and **Resume after challenge**. Completing the check in another browser does not update the agent’s session.
