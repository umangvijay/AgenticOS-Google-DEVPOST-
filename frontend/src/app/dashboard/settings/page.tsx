"use client";

import { useState, useEffect } from "react";
import { getSettings, updateSettings, UserSettings, storeCredential, pingGemini } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  const { user, updateProfile } = useAuth();
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });

  const [name, setName] = useState(user?.name || "");
  const [geminiKey, setGeminiKey] = useState("");
  const [savingKey, setSavingKey] = useState(false);
  const [grokKey, setGrokKey] = useState("");
  const [savingGrok, setSavingGrok] = useState(false);
  const [testingKey, setTestingKey] = useState(false);
  const [keyMessage, setKeyMessage] = useState({ text: "", type: "" });

  useEffect(() => {
    async function load() {
      try {
        const { settings: s } = await getSettings();
        setSettings(s);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    setSaving(true);
    setMessage({ text: "", type: "" });
    try {
      await updateSettings(settings);
      
      // Update profile if name changed
      if (name !== user?.name) {
        await updateProfile({ name });
      }

      // Apply theme
      if (settings.theme === "light") {
        document.documentElement.setAttribute("data-theme", "light");
      } else {
        document.documentElement.removeAttribute("data-theme");
      }

      setMessage({ text: "Settings saved successfully", type: "success" });
    } catch (err: unknown) {
      setMessage({ text: err instanceof Error ? err.message : "Failed to save settings", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const saveGeminiKey = async () => {
    if (!geminiKey.trim()) return;
    setSavingKey(true);
    setKeyMessage({ text: "", type: "" });
    try {
      await storeCredential("gemini", { api_key: geminiKey.trim() });
      setGeminiKey("");
      setKeyMessage({ text: "Gemini key stored in the vault. New runs will use it.", type: "success" });
    } catch (err: unknown) {
      setKeyMessage({ text: err instanceof Error ? err.message : "Could not save key", type: "error" });
    } finally {
      setSavingKey(false);
    }
  };

  const saveGrokKey = async () => {
    if (!grokKey.trim()) return;
    setSavingGrok(true);
    setKeyMessage({ text: "", type: "" });
    try {
      await storeCredential("grok", { api_key: grokKey.trim() });
      setGrokKey("");
      setKeyMessage({ text: "Grok key stored. It is used when Gemini is unavailable.", type: "success" });
    } catch (err: unknown) {
      setKeyMessage({ text: err instanceof Error ? err.message : "Could not save Grok key", type: "error" });
    } finally {
      setSavingGrok(false);
    }
  };

  const testGemini = async () => {
    setTestingKey(true);
    setKeyMessage({ text: "", type: "" });
    try {
      const res = await pingGemini();
      setKeyMessage({
        text: res.ok
          ? `Gemini is working${res.using_user_key ? " with your vault key" : " with the server key"}.`
          : `Gemini replied: ${res.reply || "unexpected response"}`,
        type: res.ok ? "success" : "error",
      });
    } catch (err: unknown) {
      setKeyMessage({
        text: err instanceof Error ? err.message : "Gemini test failed. Save your key in Settings and try again.",
        type: "error",
      });
    } finally {
      setTestingKey(false);
    }
  };

  if (loading) return (
    <div style={{ display: "flex", justifyContent: "center", padding: 100 }}>
      <div className="spinner" />
    </div>
  );

  return (
    <div className="animate-fade-in" style={{ maxWidth: 800, margin: "0 auto" }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>Settings</h1>
        <p style={{ color: "var(--text-secondary)" }}>Manage your account and AgentOS preferences.</p>
      </div>

      <form onSubmit={handleSaveSettings}>
        {message.text && (
          <div style={{
            padding: "12px 16px", marginBottom: 24,
            background: message.type === "success" ? "var(--success-subtle)" : "var(--error-subtle)", 
            borderRadius: "var(--radius-md)",
            color: message.type === "success" ? "var(--success)" : "var(--error)", 
            fontSize: 14,
          }}>
            {message.text}
          </div>
        )}

        <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, borderBottom: "1px solid var(--border-primary)", paddingBottom: 12 }}>
            Account Profile
          </h2>
          
          <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
            <div style={{
              width: 80, height: 80, borderRadius: "50%",
              background: "var(--accent-subtle)", color: "var(--accent)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 32, fontWeight: 600, flexShrink: 0
            }}>
              {user?.name?.charAt(0)?.toUpperCase() || "U"}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Full Name</label>
                <input type="text" className="input" value={name} onChange={e => setName(e.target.value)} required />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Email</label>
                <input type="email" className="input" value={user?.email || ""} disabled style={{ opacity: 0.7 }} />
              </div>
            </div>
          </div>
        </div>

        <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, borderBottom: "1px solid var(--border-primary)", paddingBottom: 12 }}>
            Agent Autonomy
          </h2>
          
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>Autonomy Level</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>How much freedom agents have to execute tools.</div>
              </div>
            </label>
            <select 
              className="input" 
              value={settings?.autonomy_level || 1}
              onChange={e => setSettings(s => s ? {...s, autonomy_level: Number(e.target.value)} : s)}
            >
              <option value={0}>Level 0: No autonomous execution (Ask for all)</option>
              <option value={1}>Level 1: Safe actions only (Default)</option>
              <option value={2}>Level 2: Moderate actions</option>
              <option value={3}>Level 3: Full autonomy (Dangerous)</option>
            </select>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
            <input 
              type="checkbox" 
              id="autoApprove"
              checked={settings?.auto_approve_low_risk || false}
              onChange={e => setSettings(s => s ? {...s, auto_approve_low_risk: e.target.checked} : s)}
              style={{ width: 16, height: 16, accentColor: "var(--accent)" }}
            />
            <label htmlFor="autoApprove" style={{ fontSize: 14, cursor: "pointer" }}>Auto-approve low risk actions</label>
          </div>
        </div>

        <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, borderBottom: "1px solid var(--border-primary)", paddingBottom: 12 }}>
            Your Gemini API key
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
            Bring your own key from Google AI Studio. It is stored encrypted in Vault as <code>gemini</code> and used for planning, MCP builds, and generation instead of the shared quota.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <input
              type="password"
              className="input"
              placeholder="AIza… or AQ.…"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              style={{ flex: 1, minWidth: 240, fontSize: 16 }}
            />
            <button type="button" className="btn btn-secondary" disabled={savingKey || !geminiKey.trim()} onClick={saveGeminiKey}>
              {savingKey ? "Saving…" : "Save key"}
            </button>
            <button type="button" className="btn btn-ghost" disabled={testingKey} onClick={testGemini}>
              {testingKey ? "Testing…" : "Test Gemini"}
            </button>
          </div>
          {keyMessage && <p style={{ marginTop: 12, fontSize: 13, color: keyMessage.type === "success" ? "var(--success)" : "var(--error)" }}>{keyMessage.text}</p>}
        </div>

        <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, borderBottom: "1px solid var(--border-primary)", paddingBottom: 12 }}>
            Grok fallback key (optional)
          </h2>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 16 }}>
            An xAI secret (usually starts with xai-). Used only when Gemini hits quota. Stored as vault name <code>grok</code>.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <input
              type="password"
              className="input"
              placeholder="xai-…"
              value={grokKey}
              onChange={(e) => setGrokKey(e.target.value)}
              style={{ flex: 1, minWidth: 240, fontSize: 16 }}
            />
            <button type="button" className="btn btn-secondary" disabled={savingGrok || !grokKey.trim()} onClick={saveGrokKey}>
              {savingGrok ? "Saving…" : "Save Grok key"}
            </button>
          </div>
        </div>

        <div className="glass-card" style={{ padding: 24, marginBottom: 32 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, borderBottom: "1px solid var(--border-primary)", paddingBottom: 12 }}>
            System Preferences
          </h2>
          
          <div style={{ display: "flex", gap: 24 }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Theme</label>
              <select 
                className="input" 
                value={settings?.theme || "dark"}
                onChange={e => setSettings(s => s ? {...s, theme: e.target.value} : s)}
              >
                <option value="dark">Dark Theme</option>
                <option value="light">Light Theme</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 6 }}>Default LLM Model</label>
              <select 
                className="input" 
                value={settings?.default_model || "gemini-3.7-flash"}
                onChange={e => setSettings(s => s ? {...s, default_model: e.target.value} : s)}
              >
                <option value="gemini-3.5-flash">Gemini 3.5 Flash</option>
                <option value="gemini-3.6-flash">Gemini 3.6 Flash</option>
                <option value="gemini-3.7-flash">Gemini 3.7 Flash</option>
                <option value="gemini-3.5-flash-lite">Gemini 3.5 Flash-Lite</option>
                <option value="gemini-3.6-flash-lite">Gemini 3.6 Flash-Lite</option>
              </select>
            </div>
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? <span className="spinner" style={{ width: 16, height: 16 }} /> : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
