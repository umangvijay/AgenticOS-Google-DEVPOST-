"use client";

import { useState, useEffect } from "react";
import PublicNavbar from "@/components/PublicNavbar";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

interface BlogPost {
  title: string;
  date: string;
  category: string;
  excerpt: string;
}

export default function BlogPage() {
  const { isAuthenticated, user } = useAuth();
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // Form State
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("Community");
  const [excerpt, setExcerpt] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Fetch blogs on mount
  useEffect(() => {
    fetch("/api/blogs")
      .then((res) => res.json())
      .then((data) => {
        setPosts(Array.isArray(data) && data.length ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load blogs", err);
        setLoading(false);
      });
  }, []);

  const handlePostBlog = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const response = await fetch("/api/blogs", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ title, category, excerpt }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to post blog");
      }

      // Success: add the new blog to the top and close modal
      setPosts([data, ...posts]);
      setIsModalOpen(false);
      setTitle("");
      setExcerpt("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const isGoogleUser = isAuthenticated && user?.auth_provider === "google";

  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <PublicNavbar />

      <main className="px-4 py-12 md:py-20 flex-1 flex flex-col items-center relative">
        <div style={{ maxWidth: 1200, width: "100%", textAlign: "center" }}>
          
          <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-12 mt-4">
            <div className="text-left">
              <h1 className="text-4xl md:text-5xl font-extrabold mb-4 gradient-text">
                AgentOS Blog
              </h1>
              <p className="text-lg md:text-xl text-[var(--text-secondary)] max-w-2xl">
                The latest news, engineering insights, and updates from the AgentOS team and community.
              </p>
            </div>
            
            {/* The Google-Restricted Create Button */}
            <div>
              {isGoogleUser ? (
                <button 
                  onClick={() => setIsModalOpen(true)}
                  className="btn btn-primary"
                  style={{ transform: "scale(1.1)", transformOrigin: "bottom right" }}
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8 }}>
                    <path d="M12 5v14M5 12h14"/>
                  </svg>
                  Create Post
                </button>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
                  <button className="btn" disabled style={{ opacity: 0.5, cursor: "not-allowed", background: "rgba(255,255,255,0.05)", border: "1px solid var(--border-primary)" }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8 }}>
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                      <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                    </svg>
                    Create Post (Locked)
                  </button>
                  <span style={{ fontSize: 13, color: "var(--text-tertiary)" }}>Requires Google Auth</span>
                </div>
              )}
            </div>
          </div>

          {/* Blog Grid (Block Content) */}
          {loading ? (
            <div style={{ display: "flex", justifyContent: "center", padding: 64 }}>
              <div className="spinner" style={{ width: 48, height: 48 }} />
            </div>
          ) : posts.length === 0 ? (
            <div className="glass-panel" style={{ padding: 48, textAlign: "center" }}>
              <h2 style={{ fontSize: 22, marginBottom: 8 }}>No posts yet</h2>
              <p style={{ color: "var(--text-secondary)" }}>Check back soon — or sign in with Google to publish the first one.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8 text-left">
              {posts.map((post, i) => (
                <div key={i} className="glass-card transition-transform hover:-translate-y-2 duration-300 flex flex-col p-6 md:p-8 cursor-pointer h-full">
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                    <span className="bg-[rgba(236,72,153,0.1)] text-[var(--accent-pink)] px-3 py-1 rounded-full text-xs font-bold">
                      {post.category}
                    </span>
                    <span style={{ color: "var(--text-tertiary)", fontSize: 13 }}>{post.date}</span>
                  </div>
                  <h2 className="text-xl md:text-2xl font-extrabold mb-4 leading-tight">{post.title}</h2>
                  <p className="text-base text-[var(--text-secondary)] leading-relaxed mb-6 flex-1">
                    {post.excerpt}
                  </p>
                  <Link href="#" className="text-primary font-bold hover:underline" style={{ marginTop: "auto" }}>
                    Read Article &rarr;
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Create Blog Modal */}
      {isModalOpen && (
        <div style={{ 
          position: "fixed", inset: 0, zIndex: 999, 
          background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)",
          display: "flex", alignItems: "center", justifyContent: "center", padding: 16
        }}>
          <div className="glass-card animate-fade-in-up w-full max-w-2xl p-6 md:p-8 bg-[var(--bg-card)] border border-[var(--border-primary)]">
            <h2 style={{ fontSize: 28, fontWeight: 800, marginBottom: 8 }}>Write a Post</h2>
            <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>Share your insights with the community. Abusive language is strictly prohibited.</p>
            
            {error && (
              <div style={{ 
                background: "rgba(239, 68, 68, 0.1)", border: "1px solid var(--error)", 
                color: "var(--error)", padding: 16, borderRadius: 8, marginBottom: 24,
                display: "flex", alignItems: "center", gap: 12
              }}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                {error}
              </div>
            )}

            <form onSubmit={handlePostBlog} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <div>
                <label style={{ display: "block", marginBottom: 8, fontSize: 14, fontWeight: 600 }}>Title</label>
                <input 
                  type="text" 
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  style={{ 
                    width: "100%", padding: "12px 16px", borderRadius: 8,
                    background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)",
                    color: "white", outline: "none"
                  }} 
                  placeholder="e.g. My first autonomous workflow"
                />
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 8, fontSize: 14, fontWeight: 600 }}>Category</label>
                <select 
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  style={{ 
                    width: "100%", padding: "12px 16px", borderRadius: 8,
                    background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)",
                    color: "white", outline: "none", appearance: "none"
                  }}
                >
                  <option value="Community">Community</option>
                  <option value="Tutorials">Tutorials</option>
                  <option value="Showcase">Showcase</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", marginBottom: 8, fontSize: 14, fontWeight: 600 }}>Content Excerpt</label>
                <textarea 
                  required
                  value={excerpt}
                  onChange={(e) => setExcerpt(e.target.value)}
                  rows={4}
                  style={{ 
                    width: "100%", padding: "12px 16px", borderRadius: 8,
                    background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-primary)",
                    color: "white", outline: "none", resize: "none"
                  }} 
                  placeholder="What's on your mind? Keep it clean!"
                />
              </div>

              <div style={{ display: "flex", gap: 16, justifyContent: "flex-end", marginTop: 8 }}>
                <button type="button" onClick={() => setIsModalOpen(false)} className="btn btn-ghost">Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? "Posting..." : "Post Blog"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
