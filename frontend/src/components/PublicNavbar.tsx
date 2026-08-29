"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";

export default function PublicNavbar() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [hidden, setHidden] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    document.body.style.overflow = isMobileMenuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [isMobileMenuOpen]);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    const titles: Record<string, string> = {
      "/": "Home · AgentOS",
      "/about": "About · AgentOS",
      "/features": "Features · AgentOS",
      "/integrations": "Integrations · AgentOS",
      "/docs": "Docs · AgentOS",
      "/faq": "FAQs · AgentOS",
      "/blog": "Blog · AgentOS",
      "/contact": "Contact · AgentOS",
      "/pricing": "Pricing · AgentOS",
      "/community": "Community · AgentOS",
      "/privacy": "Privacy · AgentOS",
      "/terms": "Terms · AgentOS",
      "/get-started": "Get started · AgentOS",
      "/login": "Sign in · AgentOS",
      "/signup": "Sign up · AgentOS",
    };
    if (titles[pathname]) document.title = titles[pathname];
    else if (pathname.startsWith("/docs/")) document.title = "Docs · AgentOS";
  }, [pathname]);

  useEffect(() => {
    let lastY = 0;
    const onScroll = () => {
      const y = window.scrollY;
      setHidden(y > 88 && y > lastY && !isMobileMenuOpen);
      lastY = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [isMobileMenuOpen]);

  const navLinks = [
    { href: "/about", label: "About Us" },
    { href: "/features", label: "Features" },
    { href: "/integrations", label: "Integrations" },
    { href: "/docs", label: "Docs" },
    { href: "/faq", label: "FAQs" },
    { href: "/blog", label: "Blog" },
    { href: "/contact", label: "Contact" },
  ];

  return (
    <>
      <header className="navbar-public" style={{
        padding: "20px clamp(16px, 5vw, 40px)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderBottom: "1px solid var(--border-primary)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        position: "sticky",
        top: 0,
        zIndex: 100,
        transform: hidden ? "translateY(-110%)" : "translateY(0)",
        transition: "transform 0.25s ease, background 0.3s ease, box-shadow 0.3s ease",
        boxShadow: "0 8px 30px rgba(43,42,39,0.04)",
        gap: 16,
      }}>
        <Link href="/" style={{ textDecoration: "none", flexShrink: 0 }} aria-label="AgentOS Home">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 32, height: 32, borderRadius: "8px",
              background: "linear-gradient(135deg, var(--accent), var(--accent-pink))",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 800, color: "white",
              boxShadow: "0 0 15px rgba(236, 72, 153, 0.4)"
            }}>
              A
            </div>
            <span style={{ fontSize: 22, fontWeight: 800, letterSpacing: "-0.5px" }} className="gradient-text">
              AgentOS
            </span>
          </div>
        </Link>

        <nav
          className="public-nav-links"
          style={{ display: "flex", gap: 28, fontSize: 14, fontWeight: 600, color: "var(--text-secondary)", flex: 1, justifyContent: "center" }}
        >
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="hover:text-[var(--text-primary)] transition-colors whitespace-nowrap"
              style={{ color: pathname === link.href ? "var(--text-primary)" : "var(--text-secondary)" }}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <Link href="/login" className="btn btn-primary whitespace-nowrap">Sign In</Link>
          <Link href="/get-started" className="btn btn-secondary whitespace-nowrap public-nav-started">Get Started</Link>
          <button
            type="button"
            className="public-nav-hamburger"
            aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
            aria-expanded={isMobileMenuOpen}
            onClick={() => setIsMobileMenuOpen((v) => !v)}
            style={{ gap: 6, background: "transparent", border: "none", width: 44, height: 44, display: "none", flexDirection: "column", justifyContent: "center", alignItems: "center", cursor: "pointer" }}
          >
            <span style={{ width: 24, height: 2, background: "var(--text-primary)", borderRadius: 2, transform: isMobileMenuOpen ? "translateY(8px) rotate(45deg)" : undefined, transition: "transform 0.2s" }} />
            <span style={{ width: 24, height: 2, background: "var(--text-primary)", borderRadius: 2, opacity: isMobileMenuOpen ? 0 : 1, transition: "opacity 0.2s" }} />
            <span style={{ width: 24, height: 2, background: "var(--text-primary)", borderRadius: 2, transform: isMobileMenuOpen ? "translateY(-8px) rotate(-45deg)" : undefined, transition: "transform 0.2s" }} />
          </button>
        </div>
      </header>

      {isMobileMenuOpen && (
        <div
          className="public-nav-overlay"
          style={{
            position: "fixed",
            inset: 0,
            top: 72,
            zIndex: 90,
            background: "var(--bg-secondary)",
            overflowY: "auto",
            padding: 24,
          }}
        >
          <nav style={{ display: "flex", flexDirection: "column", gap: 24, fontSize: 18, fontWeight: 600 }}>
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="transition-colors border-b border-[var(--border-primary)] pb-4"
                style={{ color: pathname === link.href ? "var(--text-primary)" : "var(--text-secondary)" }}
              >
                {link.label}
              </Link>
            ))}
            <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 16 }}>
              <Link href="/login" className="btn btn-primary" style={{ justifyContent: "center" }}>Sign In</Link>
              <Link href="/get-started" className="btn btn-secondary" style={{ justifyContent: "center" }}>Get Started for Free</Link>
            </div>
          </nav>
        </div>
      )}
    </>
  );
}
