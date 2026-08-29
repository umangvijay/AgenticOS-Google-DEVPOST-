export type DocSection = { h: string; p: string; bullets?: string[] };

export const DOC_PAGES: {
  slug: string;
  title: string;
  blurb: string;
  diagram: string[];
  image: string;
  sections: DocSection[];
}[] = [
  {
    slug: "user-guide",
    title: "User guide",
    blurb: "Open a workspace, send a goal, watch the agent plan and execute with live data.",
    diagram: ["You", "Workspace chat", "Planner", "Orchestrator", "Result"],
    image: "/docs/user-guide.svg",
    sections: [
      {
        h: "What you can ask",
        p: "AgentOS is a workspace, not a chatbot with canned replies. Every run hits live systems: HTTP APIs, site health, email, a real browser, code debug, project generation, and ATS resumes.",
        bullets: [
          "Check whether a public site is up, how fast it is, and which security headers it is missing.",
          "Build tools for any HTTP API from OpenAPI, a docs URL, or a description — then call those tools in the same run.",
          "Store logins in the vault and let the browser agent complete a login flow on that domain.",
          "Generate a compact, standard, or full website/app from a brief.",
          "Create or score an ATS resume against a job description.",
        ],
      },
      {
        h: "Chat workspace",
        p: "Open New chat, type a goal, press Enter. You stay on a conversation thread: your message, live agent events, and task output. Show graph reveals the DAG. Show timeline lists autonomous actions. Stop cancels an in-flight run. Failed runs can be retried.",
        bullets: [
          "OpenAPI chip / paste a spec URL to build HTTP tools, then ask to list or get.",
          "HTTP API without a spec: Build MCP tools for GitHub / Open-Meteo / PokeAPI so I can list …",
          "Website without an API: save a vault login, create MCP tools for the URL, then log in with that credential and use runOnSite.",
          "The context meter in the top bar is computed from your catalog, last run, and memory — not a fake percentage.",
        ],
      },
      {
        h: "Vault",
        p: "Credentials are encrypted with AES-256-GCM. The API never returns values after you save them. Agents refer to placeholders such as {{secret:password}}.",
        bullets: [
          "Name smtp with host, port, username, password to send mail.",
          "Name gemini with api_key to use your own Gemini quota.",
          "Name a site login for the browser agent.",
        ],
      },
      {
        h: "Roles and guest access",
        p: "Get started for free creates a guest session so you can try the workspace immediately. Guests can build MCPs, run health checks, and chat. Sign in to keep a named account.",
      },
    ],
  },
  {
    slug: "mcp-builder",
    title: "MCP tool creation",
    blurb: "If a tool is missing, AgentOS builds it, probes it live, registers it, then uses it.",
    diagram: ["Spec / URL / prompt", "Normalize", "Live probe", "Register MCP", "Call tool"],
    image: "/docs/mcp-builder.svg",
    sections: [
      {
        h: "Why this exists",
        p: "Most agents are limited to a hardcoded catalog. AgentOS treats any HTTP API as a candidate. The factory is the product — Stripe or GitHub in screenshots are examples, not the ceiling.",
      },
      {
        h: "Three ways to build",
        p: "Use Integrations → Create MCP, or ask in workspace chat. The automation agent builds the tools, then the next task in the same run (or the next message) can call them.",
        bullets: [
          "OpenAPI URL: “Create MCP tools from https://…/openapi.json then list …”. Factory fetches, normalizes, probes, registers HTTP tools.",
          "Any HTTP API (no OpenAPI): “Build MCP tools for [app] so I can [list / get / create …]”. The factory sketches a small OpenAPI from your words (or uses Gemini) against the public HTTPS host.",
          "Website (no API): Vault → save e.g. bharatenglish (username/email + password). Chat: “Create MCP tools for https://…”. Then: “Log in with vault credential bharatenglish and open home / use runOnSite …”. That is Playwright on a locked origin, not a hidden REST API.",
        ],
      },
      {
        h: "Pipeline",
        p: "Normalize → generate tool schemas → live probe against the public host → persist the MCP and cached tools → the orchestrator can call them on the next task in the same run.",
      },
      {
        h: "Safety",
        p: "Private and link-local hosts are blocked (SSRF). Generated code is AST-checked. Circuit breakers open if a tool starts failing. You can disable or delete an integration at any time.",
      },
    ],
  },
  {
    slug: "automation",
    title: "Automation agent",
    blurb: "Intent → plan → execute → recover, shown as a conversation.",
    diagram: ["Goal", "Intent", "Planner DAG", "Core / LLM tasks", "Approvals"],
    image: "/docs/automation.svg",
    sections: [
      {
        h: "The loop",
        p: "A goal becomes an intent object, then a DAG of tasks. Core nodes (HTTP, health, email) do not need a model. LLM nodes use your catalog plus Gemini. If a tool is missing, the orchestrator can invoke the MCP factory mid-run.",
      },
      {
        h: "Direct health runs",
        p: "If you ask to check the health of a URL, AgentOS can skip the planner and run core.health immediately. That path still works when Gemini quota is exhausted.",
      },
      {
        h: "Browser",
        p: "When there is no API, Chromium follows observe → decide → act on the starting domain only. Vault secrets fill login fields. CAPTCHA, OTP, and MFA pause the run: you complete them in the agent’s browser, then Resume. AgentOS does not solve or bypass those checks.",
      },
      {
        h: "Schedules and approvals",
        p: "Cron schedules fire the same goal unattended. Risky tools pause for a human decision in Approvals. Autonomy level in Settings controls how much is auto-approved.",
      },
    ],
  },
  {
    slug: "capabilities",
    title: "Capabilities",
    blurb: "Studio, health, debug, generate, resume, and memory — each is a live endpoint.",
    diagram: ["Studio", "Health", "Debug", "Generate", "Resume"],
    image: "/docs/capabilities.svg",
    sections: [
      {
        h: "Studio",
        p: "Studio is the control surface for jobs you do not want to wait on the planner for.",
        bullets: [
          "Site health: latency, TLS, redirects, missing headers, a grade.",
          "Debug: paste source and an error; get a structured diagnosis.",
          "Generate: compact / standard / full multi-file projects.",
        ],
      },
      {
        h: "Resume",
        p: "Upload a PDF against a job description, create from notes, tailor, and download HTML. Scoring is ATS-oriented (keywords, gaps, suggestions). LaTeX is not claimed unless a renderer exists.",
      },
      {
        h: "Memory",
        p: "Store notes; search is semantic (embeddings), not keyword-only. Results include a similarity score.",
      },
    ],
  },
  {
    slug: "api",
    title: "API overview",
    blurb: "REST + SSE. JWT Bearer. No demo tokens.",
    diagram: ["Client", "JWT", "REST / SSE", "Engine", "SQLite"],
    image: "/docs/api.svg",
    sections: [
      {
        h: "Auth",
        p: "POST /api/v1/auth/signup, /login, /guest, /google, /refresh. Send Authorization: Bearer <access_token>. Access tokens expire in 15 minutes; refresh lasts 7 days.",
      },
      {
        h: "Workspace",
        p: "POST /api/v1/workflows with { goal }. Poll GET /workflows/{run_id} or stream GET /workflows/{run_id}/events (SSE).",
      },
      {
        h: "Integrations",
        p: "POST /integrations/build, /build-from-url, /build-from-prompt. Poll GET /integrations/builds/{id} until status is success or error.",
      },
      {
        h: "Other",
        p: "Credentials, usage/context, capabilities/site-health, capabilities/debug, capabilities/generate, resume/create, memory, contact, settings.",
      },
    ],
  },
  {
    slug: "vision",
    title: "Vision and mission",
    blurb: "A workspace that grows the tools it needs.",
    diagram: ["Goal", "Missing tool?", "Build MCP", "Execute", "Human review"],
    image: "/docs/vision.svg",
    sections: [
      {
        h: "Vision",
        p: "You describe the outcome. The system plans, builds missing connectors, and runs against live systems — not a frozen plugin list and not a script you have to maintain by hand.",
      },
      {
        h: "Mission",
        p: "Ship an autonomous workspace that is honest about I/O: real APIs, real browsers, real mail, encrypted vaults, optional bring-your-own keys, and a conversation UI that shows what actually happened.",
      },
      {
        h: "What we will not do",
        p: "We will not pretend a hardcoded list of brand logos is “every integration.” Examples in the UI are examples. The MCP factory is how new apps arrive.",
      },
    ],
  },
  {
    slug: "byok",
    title: "Bring your own API key",
    blurb: "Use your Gemini key so runs are not blocked by the shared quota.",
    diagram: ["AI Studio key", "Settings / Vault", "Encrypted store", "gemini_client", "Your quota"],
    image: "/docs/byok.svg",
    sections: [
      {
        h: "Why",
        p: "The shared Gemini key on a free tier can return 429 RESOURCE_EXHAUSTED. Your own key keeps planning, MCP-from-prompt, debug, generate, and resume unblocked.",
      },
      {
        h: "How",
        p: "Settings → Your Gemini API key, or Vault with name gemini and field api_key. Values are encrypted and never returned. The next workflow, MCP build, debug, or generate call loads cred:gemini for your user.",
      },
      {
        h: "Fallback",
        p: "If no user key is stored, AgentOS uses GEMINI_API_KEY from the server environment.",
      },
    ],
  },
  {
    slug: "faq",
    title: "FAQ (docs)",
    blurb: "Short answers. The full accordion lives on /faq.",
    diagram: ["Ask", "Docs", "Workspace", "Vault", "Support"],
    image: "/docs/faq.svg",
    sections: [
      {
        h: "Is this a chatbot?",
        p: "The UI is chat-shaped. The engine is a planner plus DAG executor plus MCP factory. Results come from live calls.",
      },
      {
        h: "Do I need an account?",
        p: "Get started for free creates a guest workspace. Sign in when you want a durable identity.",
      },
      {
        h: "Where do I get help?",
        p: "Use the FAQ page, these docs, or Contact. Messages are emailed via SMTP to the founding team when CONTACT_SMTP_PASSWORD is a Gmail App Password (not your mailbox password).",
      },
    ],
  },
  {
    slug: "security",
    title: "Security",
    blurb: "bcrypt passwords, AES-GCM vault, CSRF, SSRF, origin-locked browser, HITL for CAPTCHA/OTP/MFA.",
    diagram: ["Password", "bcrypt", "Vault", "AES-GCM", "HITL"],
    image: "/docs/api.svg",
    sections: [
      {
        h: "Passwords",
        p: "Account passwords are bcrypt (cost 12) with a strength policy and lockout (5 failures / 15 minutes). An optional PASSWORD_PEPPER HMAC is mixed in before bcrypt. Existing unpeppered hashes still verify. Argon2id is a future option for new hashes.",
      },
      {
        h: "Vault",
        p: "API keys and site logins are AES-256-GCM. The key is derived with PBKDF2-SHA256 (480k iterations). List endpoints return names only.",
      },
      {
        h: "Network and browser",
        p: "JWT is RS256. Mutating requests need CSRF. HTTP tools block private/loopback hosts (SSRF). Browser tools stay on the start site’s registrable domain.",
      },
      {
        h: "CAPTCHA, OTP, MFA",
        p: "These are human-only. The workflow pauses (WAITING_APPROVAL). Complete the check in the open browser, then Resume. AgentOS will not fill those fields.",
      },
      {
        h: "Gmail and .env",
        p: "Contact SMTP needs a Gmail App Password in CONTACT_SMTP_PASSWORD — never your Google login password. .env is gitignored. On Cloud Run, mount the App Password from Secret Manager.",
      },
    ],
  },
  {
    slug: "deploy-gcp",
    title: "Google Cloud",
    blurb: "Optional Cloud Run hosting with $150 credits: scale to zero, Secret Manager, no .env in the image.",
    diagram: ["gcloud", "Secret Manager", "Cloud Run", "Firestore optional"],
    image: "/docs/api.svg",
    sections: [
      {
        h: "Credits",
        p: "Deploy the API with min instances 0 so idle time does not drain a new-account credit grant. An always-on worker will.",
      },
      {
        h: "Secrets",
        p: "GEMINI_API_KEY, CONTACT_SMTP_PASSWORD (App Password only), and SECRETS_MASTER_KEY go in Secret Manager. Docker never copies .env.",
      },
      {
        h: "Data",
        p: "SQLite on Cloud Run disappears when the instance scales to zero. Set STORAGE_BACKEND=firestore for durable users and runs. Commands: docs/deploy-gcp.md in the repo.",
      },
    ],
  },
];
