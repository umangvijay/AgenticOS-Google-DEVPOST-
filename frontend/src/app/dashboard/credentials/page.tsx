"use client";

import { FormEvent, useEffect, useState } from "react";
import { deleteCredential, listCredentials, storeCredential } from "@/lib/api";

export default function VaultPage() {
  const [names, setNames] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [secret, setSecret] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [info, setInfo] = useState("");

  async function load() {
    try {
      const data = await listCredentials();
      setNames(data.credentials || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load vault");
    }
  }

  useEffect(() => { void load(); }, []);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setInfo("");
    try {
      const values: Record<string, string> = {};
      if (username.trim()) values.username = username.trim();
      if (secret.trim()) values.password = secret.trim();
      if (apiKey.trim()) values.api_key = apiKey.trim();
      if (!Object.keys(values).length) {
        throw new Error("Add a username/password or an API key.");
      }
      const saved = await storeCredential(name.trim(), values);
      setInfo(`Stored “${saved.name}” with fields ${saved.fields.join(", ")}. Values are never shown again.`);
      setName("");
      setUsername("");
      setSecret("");
      setApiKey("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(cred: string) {
    if (!confirm(`Delete credential “${cred}”?`)) return;
    try {
      await deleteCredential(cred);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: 880, margin: "0 auto" }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Vault</h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>
        Encrypted with AES-256-GCM. Agents see placeholders like {"{{secret:password}}"} — never the raw value.
      </p>

      <div style={{ display: "grid", gap: 24, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
        <form className="glass-card glass-lift" style={{ padding: 24 }} onSubmit={onSave}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Store a credential</h2>
          {error && <div style={{ marginBottom: 12, color: "var(--error)", fontSize: 14 }}>{error}</div>}
          {info && <div style={{ marginBottom: 12, color: "var(--success)", fontSize: 14 }}>{info}</div>}
          <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-secondary)" }}>Name</label>
          <input className="input" required value={name} onChange={(e) => setName(e.target.value)} placeholder="gmail, pokeapi, site-login" style={{ width: "100%", marginBottom: 12 }} />
          <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-secondary)" }}>Username / email</label>
          <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" style={{ width: "100%", marginBottom: 12 }} />
          <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-secondary)" }}>Password</label>
          <input className="input" type="password" value={secret} onChange={(e) => setSecret(e.target.value)} autoComplete="new-password" style={{ width: "100%", marginBottom: 12 }} />
          <label style={{ display: "block", fontSize: 13, marginBottom: 6, color: "var(--text-secondary)" }}>API key (optional)</label>
          <input className="input" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="For HTTP MCPs" autoComplete="off" style={{ width: "100%", marginBottom: 16 }} />
          <button className="btn btn-primary" type="submit" disabled={busy} style={{ width: "100%" }}>
            {busy ? "Encrypting…" : "Save to vault"}
          </button>
        </form>

        <div className="glass-card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Stored names</h2>
          {names.length === 0 ? (
            <p style={{ color: "var(--text-tertiary)", fontSize: 14 }}>Nothing stored yet.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 8 }}>
              {names.map((cred) => (
                <li key={cred} className="glass-panel" style={{ padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", borderRadius: 12 }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 14 }}>{cred}</span>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => void onDelete(cred)}>Delete</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
