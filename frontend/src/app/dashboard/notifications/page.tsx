"use client";

import { useState, useEffect } from "react";
import { listNotifications, markNotificationRead, markAllNotificationsRead, Notification } from "@/lib/api";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [unreadOnly, setUnreadOnly] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await listNotifications(unreadOnly, 50);
      setNotifications(data.notifications);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [unreadOnly]);

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      console.error("Failed to mark read", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    } catch (err) {
      console.error("Failed to mark all read", err);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: 800, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700 }}>Notifications</h1>
          <p style={{ color: "var(--text-secondary)" }}>Stay updated on agent activities and approvals.</p>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button 
            className={`btn ${unreadOnly ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setUnreadOnly(!unreadOnly)}
          >
            {unreadOnly ? "Showing Unread" : "Show Unread Only"}
          </button>
          <button className="btn btn-secondary" onClick={handleMarkAllRead}>Mark All Read</button>
        </div>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", marginBottom: 20, background: "var(--error-subtle)", borderRadius: "var(--radius-md)", color: "var(--error)", fontSize: 14 }}>
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="skeleton" style={{ height: 80 }} />
          <div className="skeleton" style={{ height: 80 }} />
        </div>
      ) : notifications.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {notifications.map(notif => (
            <div key={notif.id} className="glass-card" style={{ 
              padding: 20, 
              borderLeft: notif.is_read ? "1px solid var(--border-primary)" : "3px solid var(--accent)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                <h3 style={{ fontSize: 16, fontWeight: notif.is_read ? 500 : 700, color: notif.is_read ? "var(--text-secondary)" : "var(--text-primary)", margin: 0 }}>
                  {notif.title}
                </h3>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
                    {new Date(notif.created_at).toLocaleString()}
                  </span>
                  {!notif.is_read && (
                    <button className="btn btn-ghost btn-sm" onClick={() => handleMarkRead(notif.id)} style={{ padding: "4px 8px" }}>
                      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>
                    </button>
                  )}
                </div>
              </div>
              <p style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 0 }}>
                {notif.body}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-card empty-state">
          <svg width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1" viewBox="0 0 24 24">
            <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <h3 style={{ fontSize: 16, fontWeight: 500, color: "var(--text-primary)", marginBottom: 8 }}>All caught up!</h3>
          <p style={{ marginBottom: 0 }}>You have no {unreadOnly ? "unread " : ""}notifications.</p>
        </div>
      )}
    </div>
  );
}
