"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { submitGoal, GoalAttachment } from "@/lib/api";

const SUGGESTIONS = [
  { label: "OpenAPI MCP", goal: "Create MCP tools from https://raw.githubusercontent.com/PokeAPI/pokeapi/master/openapi.yml then list pokemon" },
  { label: "HTTP API MCP", goal: "Build MCP tools for GitHub so I can list public events, then list them" },
  { label: "Website MCP", goal: "Create MCP tools for https://example.com then open home and summarize the page" },
];

const TEXT_TYPES = [
  "text/",
  "application/json",
  "application/xml",
  "application/javascript",
  "application/x-yaml",
  "application/yaml",
];
const TEXT_EXTS = [".txt", ".md", ".json", ".csv", ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".yml", ".yaml", ".xml", ".log", ".env", ".sql"];
const MAX_ATTACH = 5;
const MAX_BYTES = 4 * 1024 * 1024;
const MAX_TEXT = 12000;

type Attached = GoalAttachment & { id: string; kind: "file" | "photo" };

function isTextFile(file: File) {
  if (TEXT_TYPES.some((t) => file.type.startsWith(t) || file.type === t)) return true;
  const name = file.name.toLowerCase();
  return TEXT_EXTS.some((ext) => name.endsWith(ext));
}

async function fileToAttachment(file: File, kind: "file" | "photo"): Promise<Attached> {
  if (file.size > MAX_BYTES) {
    throw new Error(`${file.name} is larger than 4 MB.`);
  }
  const base = { id: `${file.name}-${file.size}-${Date.now()}`, name: file.name, mime: file.type || "application/octet-stream", kind };
  if (kind === "photo" || file.type.startsWith("image/")) {
    const image_base64 = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result || "");
        const comma = result.indexOf(",");
        resolve(comma >= 0 ? result.slice(comma + 1) : result);
      };
      reader.onerror = () => reject(reader.error || new Error("Could not read photo"));
      reader.readAsDataURL(file);
    });
    return { ...base, kind: "photo", mime: file.type || "image/jpeg", image_base64 };
  }
  if (isTextFile(file)) {
    const text = (await file.text()).slice(0, MAX_TEXT);
    return { ...base, text };
  }
  return base;
}

export default function ChatComposer({
  compact = false,
  disabled = false,
  threadId,
  parentRunId,
  onRunCreated,
}: {
  compact?: boolean;
  disabled?: boolean;
  threadId?: string;
  parentRunId?: string;
  onRunCreated?: (res: { run_id: string; thread_id?: string }) => void;
}) {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [attachments, setAttachments] = useState<Attached[]>([]);
  const menuRef = useRef<HTMLDivElement>(null);
  const photoRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  async function addFiles(list: FileList | null, kind: "file" | "photo") {
    if (!list?.length) return;
    setError("");
    const next = [...attachments];
    for (const file of Array.from(list)) {
      if (next.length >= MAX_ATTACH) {
        setError(`You can attach up to ${MAX_ATTACH} items.`);
        break;
      }
      try {
        next.push(await fileToAttachment(file, kind));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Could not read that file");
      }
    }
    setAttachments(next);
    setMenuOpen(false);
    if (photoRef.current) photoRef.current.value = "";
    if (fileRef.current) fileRef.current.value = "";
  }

  async function send(text?: string) {
    const value = (text ?? goal).trim();
    if ((!value && attachments.length === 0) || loading || disabled) return;
    setError("");
    setLoading(true);
    try {
      const payload = attachments.map(({ name, mime, text: body, image_base64 }) => ({
        name, mime, text: body, image_base64,
      }));
      const prompt = value || "Use the attached files and photos to complete the request.";
      const res = await submitGoal(prompt, payload, {
        parent_run_id: parentRunId,
        thread_id: threadId,
      });
      setGoal("");
      setAttachments([]);
      if (onRunCreated) {
        onRunCreated(res);
        setLoading(false);
      } else {
        router.push(`/dashboard/workspace/${res.run_id}`);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start the run");
      setLoading(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await send();
  }

  return (
    <form onSubmit={handleSubmit} className="chat-composer">
      {error && (
        <div style={{
          padding: "10px 14px", marginBottom: 12, background: "var(--error-subtle)",
          borderRadius: 12, color: "var(--error)", fontSize: 13, lineHeight: 1.45,
        }}>
          {error}
        </div>
      )}
      {attachments.length > 0 && (
        <div className="attach-chip-row">
          {attachments.map((a) => (
            <span key={a.id} className="attach-chip">
              {a.kind === "photo" ? "Photo" : "File"} · {a.name}
              <button type="button" aria-label={`Remove ${a.name}`} onClick={() => setAttachments((prev) => prev.filter((x) => x.id !== a.id))}>
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="glass-panel chat-composer-box composer-pill">
        <div className="composer-row">
          <div className="composer-plus-wrap" ref={menuRef}>
            <button
              type="button"
              className="composer-plus"
              title="Add photos, files, or an MCP"
              aria-label="Add photos, files, or an MCP"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
              disabled={disabled || loading}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
            {menuOpen && (
              <div className="attach-menu" role="menu">
                <button type="button" role="menuitem" onClick={() => photoRef.current?.click()}>
                  Add photos
                </button>
                <button type="button" role="menuitem" onClick={() => fileRef.current?.click()}>
                  Add files
                </button>
                <Link href="/dashboard/integrations/create" role="menuitem" onClick={() => setMenuOpen(false)}>
                  Create an MCP
                </Link>
              </div>
            )}
            <input
              ref={photoRef}
              type="file"
              accept="image/*"
              multiple
              hidden
              onChange={(e) => void addFiles(e.target.files, "photo")}
            />
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.json,.csv,.py,.js,.ts,.tsx,.html,.css,.yml,.yaml,.xml,.log,.sql,text/*,application/json"
              multiple
              hidden
              onChange={(e) => void addFiles(e.target.files, "file")}
            />
          </div>
          <textarea
            className="input chat-input"
            placeholder={disabled ? "AgentOS is working…" : "Ask anything. AgentOS will plan, build missing tools, and do the work."}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            disabled={loading || disabled}
            rows={compact ? 1 : 2}
          />
          <button type="submit" className="send-orb" disabled={disabled || (!goal.trim() && attachments.length === 0) || loading} aria-label="Send">
            {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <path d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            )}
          </button>
        </div>
      </div>
      {!compact && (
        <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
          {SUGGESTIONS.map((s) => (
            <button key={s.label} type="button" className="badge badge-neutral suggestion-chip" onClick={() => void send(s.goal)}>
              {s.label}
            </button>
          ))}
        </div>
      )}
    </form>
  );
}
