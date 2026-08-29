"use client";

import ChatComposer from "@/components/ChatComposer";

export default function DashboardPage() {
  return (
    <div className="workspace-home animate-fade-in-up">
      <div className="workspace-hero">
        <h1 className="workspace-title">Where should we begin?</h1>
        <p className="workspace-sub">
          Tell AgentOS what you want. It plans the work, builds any missing app tools, and runs them live.
        </p>
      </div>

      <div className="workspace-composer-wrap">
        <ChatComposer />
      </div>

      <div className="mcp-howto glass-panel">
        <h2>How to use MCP tools from chat</h2>
        <ol>
          <li>
            <strong>OpenAPI URL.</strong> Paste the spec: “Create MCP tools from https://…/openapi.json then list …”
          </li>
          <li>
            <strong>Any HTTP API (no OpenAPI).</strong> “Build MCP tools for [app] so I can [list / get / create …]”
          </li>
          <li>
            <strong>Website (no API).</strong> Vault → save e.g. <code>bharatenglish</code> (username/email + password).
            Chat: “Create MCP tools for https://…”. Then: “Log in with vault credential bharatenglish and open home / use runOnSite …”
          </li>
        </ol>
        <p>
          The factory registers real tools (HTTP from OpenAPI or a sketched REST spec; websites get origin-locked browser tools). The next message in this thread reuses them. CAPTCHA/OTP/MFA pause for you — AgentOS does not solve them.
        </p>
      </div>
    </div>
  );
}
