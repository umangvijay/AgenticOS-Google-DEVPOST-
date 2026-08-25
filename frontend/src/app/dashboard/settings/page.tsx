"use client";

import { useState, useEffect } from "react";
import { getSettings, updateSettings, UserSettings } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  const { user, updateProfile } = useAuth();
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });

  const [name, setName] = useState(user?.name || "");

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
                value={settings?.default_model || "gemini-3.5-flash"}
                onChange={e => setSettings(s => s ? {...s, default_model: e.target.value} : s)}
              >
                <option value="gemini-3.5-flash">Gemini 3.5 Flash (Fast)</option>
                <option value="gemini-3.5-pro">Gemini 3.5 Pro (Reasoning)</option>
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
