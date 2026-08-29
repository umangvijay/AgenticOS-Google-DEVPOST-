"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { DOC_PAGES } from "@/content/docs";

export default function DocsToc({ currentSlug }: { currentSlug: string }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [currentSlug]);

  return (
    <div className="docs-toc-slot">
      <button
        type="button"
        className="docs-toc-toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide docs menu" : "Docs menu"}
      </button>
      <aside className={`docs-toc glass-panel ${open ? "is-open" : ""}`}>
        <p className="eyebrow">Docs</p>
        {DOC_PAGES.map((p) => (
          <Link
            key={p.slug}
            href={`/docs/${p.slug}`}
            className={p.slug === currentSlug ? "docs-toc-link active" : "docs-toc-link"}
          >
            {p.title}
          </Link>
        ))}
        <Link href="/faq" className="docs-toc-link">FAQs</Link>
      </aside>
    </div>
  );
}
