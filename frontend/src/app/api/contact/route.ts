import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";

const TO = process.env.CONTACT_TO_EMAIL || "godumang35@gmail.com";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function inboxPath() {
  return path.join(process.cwd(), "data", "contact_inbox.json");
}

function persist(record: unknown) {
  const file = inboxPath();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  let existing: unknown[] = [];
  try {
    if (fs.existsSync(file)) {
      const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
      if (Array.isArray(parsed)) existing = parsed;
    }
  } catch { /* ignore */ }
  existing.unshift(record);
  fs.writeFileSync(file, JSON.stringify(existing.slice(0, 500), null, 2));
}

export async function GET() {
  try {
    const backend = await fetch(`${API}/contact/status`, { cache: "no-store" });
    const data = await backend.json().catch(() => ({}));
    if (!backend.ok) {
      return NextResponse.json({ smtp_configured: false, to: TO, setup: data.setup || "" });
    }
    return NextResponse.json({
      smtp_configured: Boolean(data.smtp_configured),
      to: data.to || TO,
      host: data.host || null,
      setup: data.setup || "",
    });
  } catch {
    return NextResponse.json({ smtp_configured: false, to: TO, setup: "Start the AgentOS backend, then set CONTACT_SMTP_PASSWORD in .env." });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const email = String(body.email || "").trim();
    const message = String(body.message || "").trim();
    const name = String(body.name || "").trim();
    if (!email.includes("@") || !message) {
      return NextResponse.json({ error: "Email and a message are required." }, { status: 400 });
    }
    persist({ at: new Date().toISOString(), name, email, message, to: TO });

    try {
      const backend = await fetch(`${API}/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, name, message }),
      });
      const data = await backend.json().catch(() => ({}));
      if (!backend.ok) {
        return NextResponse.json(
          { error: data.detail || data.error || "Could not send message", saved: true, delivered: false, to: TO },
          { status: backend.status },
        );
      }
      return NextResponse.json({
        ok: true,
        saved: Boolean(data.saved ?? true),
        delivered: Boolean(data.delivered),
        to: data.to || TO,
        via: data.via || null,
        reason: data.reason || null,
        message: data.message || (data.delivered
          ? `Message emailed to ${TO}.`
          : `Message saved. Email was not delivered yet.`),
      });
    } catch {
      return NextResponse.json({
        ok: true,
        saved: true,
        delivered: false,
        to: TO,
        reason: "backend_unreachable",
        message: `Message saved locally. The API at ${API} did not accept it — start the backend and send again.`,
      });
    }
  } catch {
    return NextResponse.json({ error: "Could not send message" }, { status: 500 });
  }
}
