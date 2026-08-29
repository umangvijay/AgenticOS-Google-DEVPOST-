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
    </div>
  );
}
