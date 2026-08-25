"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useState, useEffect, ReactNode, useRef } from "react";
import { getUnreadCount, listNotifications, markNotificationRead, markAllNotificationsRead, Notification } from "@/lib/api";

// ── Navigation Items ─────────────────────────────────────────────
const NAV_ITEMS = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: (
      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
  },
  {
    label: "Workflows",
    href: "/dashboard/workflows",
    icon: (
      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
      </svg>
    ),
  },
  {
    label: "Integrations",
    href: "/dashboard/integrations",
    icon: (
      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M12 2v6m0 8v6M2 12h6m8 0h6" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    ),
  },
  {
    label: "Resume",
    href: "/dashboard/resume",
    icon: (
      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
      </svg>
    ),
  },
  {
    label: "Schedules",
    href: "/dashboard/schedules",
    icon: (
      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 6v6l4 2" />
      </svg>
    ),
  },
  {
    label: "Settings",
    href: "/dashboard/settings",
    icon: (
      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" />
      </svg>
    ),
  },
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  
  // Notification Panel State
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);

  // Auth guard
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Poll unread notifications
  useEffect(() => {
    if (!isAuthenticated) return;
    const poll = async () => {
      try {
        const data = await getUnreadCount();
        setUnreadCount(data.unread_count);
      } catch { /* ignore */ }
    };
    poll();
    const interval = setInterval(poll, 15000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Load notifications when panel opens
  useEffect(() => {
    if (showNotifications) {
      const loadNotifs = async () => {
        try {
          const res = await listNotifications();
          setNotifications(res.notifications);
        } catch { /* ignore */ }
      };
      loadNotifs();
    }
  }, [showNotifications]);

  // Click outside to close panel
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    if (showNotifications) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showNotifications]);

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id);
      setNotifications(prev => prev.filter(n => n.id !== id));
      setUnreadCount(Math.max(0, unreadCount - 1));
    } catch { /* ignore */ }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications([]);
      setUnreadCount(0);
    } catch { /* ignore */ }
  };

  if (isLoading) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="spinner" style={{ width: 32, height: 32 }} />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* ── Sidebar ────────────────────────────────────────────── */}
      <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
        {/* Logo */}
        <Link href="/" style={{ textDecoration: "none" }}>
          <div style={{
            padding: "20px 16px", display: "flex", alignItems: "center",
            gap: 12, borderBottom: "1px solid var(--border-primary)",
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: "var(--radius-md)",
              background: "linear-gradient(135deg, var(--accent), #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18, fontWeight: 800, color: "white", flexShrink: 0,
            }}>
              A
            </div>
            {!collapsed && (
              <span style={{ fontSize: 18, fontWeight: 700 }} className="gradient-text">
                AgentOS
              </span>
            )}
          </div>
        </Link>

        {/* Nav items */}
        <nav style={{ flex: 1, padding: "12px 0", overflowY: "auto" }}>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-nav-item ${pathname === item.href ? "active" : ""}`}
              title={collapsed ? item.label : undefined}
            >
              {item.icon}
              {!collapsed && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Collapse button */}
        <div style={{ padding: "12px 8px", borderTop: "1px solid var(--border-primary)" }}>
          <button
            className="sidebar-nav-item"
            onClick={() => setCollapsed(!collapsed)}
            style={{ width: "100%" }}
          >
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"
              style={{ transform: collapsed ? "rotate(180deg)" : undefined, transition: "transform 0.3s" }}>
              <path d="M11 17l-5-5 5-5M17 17l-5-5 5-5" />
            </svg>
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* ── Main content ───────────────────────────────────────── */}
      <div className={`main-content ${collapsed ? "sidebar-collapsed" : ""}`} style={{ flex: 1 }}>
        {/* Topbar */}
        <header className="topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <h1 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
              {NAV_ITEMS.find((i) => pathname.startsWith(i.href))?.label || "AgentOS"}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {/* Notification bell */}
            <div style={{ position: "relative" }} ref={panelRef}>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setShowNotifications(!showNotifications)}
                style={{ position: "relative" }}
              >
                <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                  <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0" />
                </svg>
                {unreadCount > 0 && (
                  <span style={{
                    position: "absolute", top: 0, right: 0,
                    width: 16, height: 16, borderRadius: "50%",
                    background: "var(--error)", color: "white",
                    fontSize: 10, fontWeight: 700,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </button>

              {/* Notification Slide-Out Panel */}
              {showNotifications && (
                <div className="glass-card animate-slide-in" style={{
                  position: "absolute", top: "100%", right: 0, width: 360,
                  marginTop: 8, zIndex: 100, display: "flex", flexDirection: "column",
                  maxHeight: "80vh", overflow: "hidden", border: "1px solid var(--border-primary)"
                }}>
                  <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-primary)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Notifications</h3>
                    {notifications.length > 0 && (
                      <button onClick={handleMarkAllRead} className="btn btn-ghost btn-sm" style={{ fontSize: 12 }}>
                        Mark all read
                      </button>
                    )}
                  </div>
                  
                  <div style={{ flex: 1, overflowY: "auto", padding: "12px 0" }}>
                    {notifications.length === 0 ? (
                      <div style={{ padding: 32, textAlign: "center", color: "var(--text-tertiary)", fontSize: 14 }}>
                        All caught up! Your agents are running smoothly.
                      </div>
                    ) : (
                      notifications.map(n => (
                        <div key={n.id} style={{ 
                          padding: "12px 20px", borderBottom: "1px solid var(--border-primary)",
                          background: !n.is_read ? "var(--bg-tertiary)" : "transparent",
                          display: "flex", gap: 12, alignItems: "flex-start", position: "relative"
                        }}>
                          <div style={{
                            width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
                            background: n.type === "APPROVAL_REQUIRED" ? "var(--warning-subtle)" :
                                        n.type === "WORKFLOW_FAILED" ? "var(--error-subtle)" :
                                        n.type === "WORKFLOW_COMPLETED" ? "var(--success-subtle)" : "var(--info-subtle)",
                            color: n.type === "APPROVAL_REQUIRED" ? "var(--warning)" :
                                   n.type === "WORKFLOW_FAILED" ? "var(--error)" :
                                   n.type === "WORKFLOW_COMPLETED" ? "var(--success)" : "var(--info)",
                            display: "flex", alignItems: "center", justifyContent: "center"
                          }}>
                            {n.type === "APPROVAL_REQUIRED" ? "⚠️" : n.type === "WORKFLOW_COMPLETED" ? "✓" : "!"}
                          </div>
                          <div style={{ flex: 1, paddingRight: 24 }}>
                            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                              {n.title}
                            </div>
                            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8, lineHeight: 1.4 }}>
                              {n.body}
                            </div>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                              <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
                                {new Date(n.created_at).toLocaleTimeString()}
                              </span>
                              {Boolean(n.metadata?.workflow_id) && (
                                <Link 
                                  href={`/dashboard/workflows/${n.metadata.workflow_id as string}`}
                                  className="btn btn-secondary btn-sm"
                                  style={{ padding: "4px 8px", fontSize: 11 }}
                                  onClick={() => setShowNotifications(false)}
                                >
                                  View
                                </Link>
                              )}
                            </div>
                          </div>
                          
                          <button 
                            className="btn btn-ghost" 
                            style={{ position: "absolute", top: 12, right: 12, padding: 4, minWidth: 0, height: "auto" }}
                            onClick={(e) => { e.stopPropagation(); handleMarkRead(n.id); }}
                            title="Dismiss"
                          >
                            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M18 6L6 18M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* User menu */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 32, height: 32, borderRadius: "50%",
                background: "var(--accent-subtle)", color: "var(--accent)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 14, fontWeight: 600,
              }}>
                {user?.name?.charAt(0)?.toUpperCase() || "U"}
              </div>
              <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)" }}>
                {user?.name || "User"}
              </span>
              <button className="btn btn-ghost btn-sm" onClick={logout} title="Sign out">
                <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
                </svg>
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{ padding: 24 }}>
          {children}
        </main>
      </div>
    </div>
  );
}
