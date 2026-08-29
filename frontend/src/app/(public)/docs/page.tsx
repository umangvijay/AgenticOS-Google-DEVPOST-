import PublicNavbar from "@/components/PublicNavbar";
import Link from "next/link";
import { DOC_PAGES } from "@/content/docs";

export default function DocsIndexPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh" }}>
      <PublicNavbar />
      <main className="px-4 py-12 md:py-20" style={{ maxWidth: 1080, margin: "0 auto" }}>
        <p className="eyebrow">Documentation</p>
        <h1 className="gradient-text apple-hero" style={{ fontSize: "clamp(36px, 6vw, 64px)", fontWeight: 800, marginBottom: 12 }}>
          How AgentOS works
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 18, maxWidth: 640, marginBottom: 40 }}>
          Plans, MCP creation, live execution, vaults, and your own API keys — with diagrams on every page.
        </p>
        <div className="docs-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 18 }}>
          {DOC_PAGES.map((p) => (
            <Link key={p.slug} href={`/docs/${p.slug}`} className="glass-panel docs-card" style={{ padding: 0, textDecoration: "none", overflow: "hidden" }}>
              <div className="docs-card-art">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={p.image} alt="" width={400} height={140} />
              </div>
              <div style={{ padding: 20 }}>
                <h2 style={{ fontSize: 18, margin: "0 0 8px", color: "var(--text-primary)" }}>{p.title}</h2>
                <p style={{ margin: 0, color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.5 }}>{p.blurb}</p>
              </div>
            </Link>
          ))}
        </div>
        <div className="glass-panel" style={{ marginTop: 36, padding: 28, display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <h2 style={{ margin: "0 0 6px", fontSize: 22 }}>Still stuck?</h2>
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>Accordion answers for guests, keys, MCP builds, and quota errors.</p>
          </div>
          <Link href="/faq" className="btn btn-primary">Open FAQs</Link>
        </div>
      </main>
    </div>
  );
}
