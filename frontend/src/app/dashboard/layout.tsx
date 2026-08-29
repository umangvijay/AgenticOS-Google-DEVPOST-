"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useState, useEffect, ReactNode, useRef } from "react";
import { getUnreadCount, listNotifications, markNotificationRead, markAllNotificationsRead, listWorkflows, Notification, WorkflowRun } from "@/lib/api";
import ContextUsageButton from "@/components/ContextUsage";

// ── Navigation Items ─────────────────────────────────────────────
const NEW_CHAT = {
  label: "New chat",
  href: "/dashboard",
  icon: (
    <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
      <path d="M12 5v14M5 12h14" />
    </svg>
  ),
};

const NAV_ITEMS = [
  {
    label: "Runs",
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
    label: "Studio",
    href: "/dashboard/studio",
    icon: (
      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M12 20h9M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
      </svg>
    ),
  },
  {
    label: "Vault",
    href: "/dashboard/credentials",
    icon: (
      <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <rect x="3" y="11" width="18" height="11" rx="2" />
        <path d="M7 11V7a5 5 0 0110 0v4" />
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
  return <DashboardInner>{children}</DashboardInner>;
}

function DashboardInner({ children }: { children: ReactNode }) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [recents, setRecents] = useState<WorkflowRun[]>([]);
  
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

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("agentos_sidebar_collapsed");
      if (stored === "1") setCollapsed(true);
      if (stored === "0") setCollapsed(false);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem("agentos_sidebar_collapsed", collapsed ? "1" : "0");
    } catch { /* ignore */ }
  }, [collapsed]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const apply = () => {
      setIsMobile(mq.matches);
      if (!mq.matches) setMobileOpen(false);
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  function toggleSidebar() {
    if (isMobile) setMobileOpen((v) => !v);
    else setCollapsed((v) => !v);
  }

  const showLabels = isMobile ? mobileOpen : !collapsed;

  useEffect(() => {
    if (!isAuthenticated) return;
    const load = async () => {
      try {
        const data = await listWorkflows(50);
        setRecents((data.workflows || []).filter((wf) => !wf.parent_run_id));
      } catch { /* ignore */ }
    };
    load();
    const interval = setInterval(load, 8000);
    return () => clearInterval(interval);
  }, [isAuthenticated, pathname]);

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

  if (isLoading || !isAuthenticated) {
    return (
      <div className="mesh-gradient" style={{ minHeight: "100dvh", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
        <div className="glass-card" style={{ textAlign: "center", maxWidth: 420, padding: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Sign in to AgentOS</h1>
          <p style={{ color: "var(--text-secondary)", marginBottom: 20 }}>
            The dashboard is for an authenticated session. Sign in, or Get Started as a guest.
          </p>
          {isLoading && <div className="spinner" style={{ width: 28, height: 28, margin: "0 auto 16px" }} />}
          <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
            <Link href="/login" className="btn btn-primary">Sign In</Link>
            <Link href="/get-started" className="btn btn-secondary">Get Started</Link>
          </div>
        </div>
      </div>
    );
  }

  const isWorkspace = pathname === "/dashboard" || pathname.startsWith("/dashboard/workspace");
  const pageTitle =
    NAV_ITEMS.find((i) => pathname.startsWith(i.href))?.label
    || (pathname.startsWith("/dashboard/workspace") ? "Chat" : "New chat");

  return (
    <div className="mesh-gradient dashboard-shell">
      {/* ── Sidebar ────────────────────────────────────────────── */}
      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div 
          className="lg:hidden" 
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 900 }}
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside className={`sidebar ${!isMobile && collapsed ? "collapsed" : ""} ${mobileOpen ? "mobile-open" : ""}`}>
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
            {showLabels && (
              <span style={{ fontSize: 18, fontWeight: 700 }} className="gradient-text">
                AgentOS
              </span>
            )}
          </div>
        </Link>

        <nav className="sidebar-scroll hide-scrollbar">
          <Link
            href={NEW_CHAT.href}
            className={`sidebar-nav-item ${pathname === "/dashboard" ? "active" : ""}`}
            title={!showLabels ? NEW_CHAT.label : undefined}
            onClick={() => setMobileOpen(false)}
          >
            {NEW_CHAT.icon}
            {showLabels && <span>{NEW_CHAT.label}</span>}
          </Link>

          {showLabels && (
            <div className="sidebar-section-label">Recents</div>
          )}
          {showLabels && recents.slice(0, 14).map((wf) => (
            <Link
              key={wf.run_id}
              href={`/dashboard/workspace/${wf.run_id}`}
              className={`sidebar-recent ${pathname === `/dashboard/workspace/${wf.run_id}` || pathname === `/dashboard/workspace/${wf.thread_id || ""}` ? "active" : ""}`}
              onClick={() => setMobileOpen(false)}
              title={wf.goal}
            >
              <span className="truncate">{wf.goal}</span>
            </Link>
          ))}
          {showLabels && recents.length === 0 && (
            <div className="sidebar-empty">No chats yet</div>
          )}

          {showLabels && <div className="sidebar-section-label">Workspace</div>}
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`sidebar-nav-item ${pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href)) ? "active" : ""}`}
              title={!showLabels ? item.label : undefined}
              onClick={() => setMobileOpen(false)}
            >
              {item.icon}
              {showLabels && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        <div style={{ padding: "8px 8px 4px", borderTop: "1px solid var(--border-primary)" }}>
          <button
            className="sidebar-nav-item"
            onClick={toggleSidebar}
            style={{ width: "100%" }}
            title={showLabels ? "Collapse sidebar" : "Expand sidebar"}
          >
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"
              style={{ transform: showLabels ? undefined : "rotate(180deg)", transition: "transform 0.3s" }}>
              <path d="M11 17l-5-5 5-5M17 17l-5-5 5-5" />
            </svg>
            {showLabels && <span>Collapse</span>}
          </button>
          <div className="sidebar-user">
            <div className="sidebar-avatar">{user?.name?.charAt(0)?.toUpperCase() || "U"}</div>
            {showLabels && (
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="truncate" style={{ fontSize: 13, fontWeight: 600 }}>{user?.name || "User"}</div>
                <div className="truncate" style={{ fontSize: 11, color: "var(--text-tertiary)" }}>{user?.email || ""}</div>
              </div>
            )}
            <button className="btn btn-ghost btn-sm" style={{ padding: 6, flexShrink: 0 }} onClick={logout} title="Sign out">
              <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
                <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main content ───────────────────────────────────────── */}
      <div className={`main-content ${!isMobile && collapsed ? "sidebar-collapsed" : ""}`} style={{ flex: 1 }}>
        {/* Topbar */}
        <header className="topbar">
          <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minWidth: 0 }}>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ padding: 4, flexShrink: 0 }}
              onClick={toggleSidebar}
              aria-label={showLabels ? "Collapse sidebar" : "Expand sidebar"}
              title={showLabels ? "Collapse sidebar" : "Expand sidebar"}
            >
              <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="truncate" style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
              {pageTitle}
            </h1>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
            <ContextUsageButton />
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
                  position: "absolute", top: "100%", right: 0, width: "min(360px, calc(100vw - 24px))",
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

          </div>
        </header>

        <main className={`dashboard-main ${isWorkspace ? "is-workspace" : ""}`} style={isWorkspace ? undefined : { padding: "clamp(16px, 3vw, 28px)" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
