import PublicNavbar from "@/components/PublicNavbar";
import DocsToc from "@/components/DocsToc";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DOC_PAGES } from "@/content/docs";

export function generateStaticParams() {
  return DOC_PAGES.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = DOC_PAGES.find((p) => p.slug === slug);
  return { title: page?.title || "Docs" };
}

export default async function DocArticle({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = DOC_PAGES.find((p) => p.slug === slug);
  if (!page) notFound();

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh" }}>
      <PublicNavbar />
      <div className="docs-layout">
        <DocsToc currentSlug={slug} />
        <article className="docs-article">
          <Link href="/docs" style={{ fontSize: 13, color: "var(--accent)", textDecoration: "none" }}>← All docs</Link>
          <h1 className="apple-hero" style={{ fontSize: "clamp(28px, 5vw, 44px)", margin: "12px 0 16px" }}>{page.title}</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 18, lineHeight: 1.6, marginBottom: 28 }}>{page.blurb}</p>

          <div className="docs-hero-art glass-panel">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={page.image} alt={`${page.title} diagram`} width={720} height={280} />
          </div>

          <div className="flow-diagram glass-panel" style={{ padding: 20, margin: "28px 0" }}>
            <p className="eyebrow">Flow</p>
            <div className="flow-row">
              {page.diagram.map((step, i) => (
                <div key={step} className="flow-node">
                  <span className="flow-index">0{i + 1}</span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>

          {page.sections.map((s) => (
            <section key={s.h} className="docs-section">
              <h2>{s.h}</h2>
              <p>{s.p}</p>
              {s.bullets && (
                <ul>
                  {s.bullets.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </article>
      </div>
    </div>
  );
}
