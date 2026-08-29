import Link from "next/link";
import Image from "next/image";
import PublicNavbar from "@/components/PublicNavbar";

export default function AboutPage() {
  return (
    <div className="mesh-gradient" style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      {/* Navbar */}
      <PublicNavbar />

      <main className="px-6 py-16 md:px-10 md:py-24 max-w-3xl mx-auto flex-1 w-full text-center">
        <h1 className="text-5xl md:text-6xl font-black mb-8 tracking-tight gradient-text">
          About Us
        </h1>
        <p className="text-xl md:text-2xl text-[var(--text-secondary)] mb-16 leading-relaxed font-medium">
          We are building the future of autonomous workspaces. 
          AgentOS was created with a singular vision: an AI assistant shouldn't be limited by the tools its developers hardcoded for it.
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-24 text-left">
          <div className="glass-card p-8 md:p-10 border-t-4 md:border-t-0 md:border-l-4 border-t-[var(--accent-pink)] md:border-l-[var(--accent-pink)]">
            <h2 className="text-2xl font-bold mb-4">Our Mission</h2>
            <p className="text-[var(--text-secondary)] leading-relaxed">
              Our mission is to bridge the gap between static automation platforms and true artificial general intelligence.
              When you give a goal to AgentOS, it doesn't just execute predefined scripts. It reasons about the required steps,
              searches for missing capabilities, reads documentation, and physically writes the software it needs to accomplish your goal.
            </p>
          </div>
          <div className="glass-card p-8 md:p-10 border-t-4 md:border-t-0 md:border-l-4 border-t-[var(--accent-purple)] md:border-l-[var(--accent-purple)]">
            <h2 className="text-2xl font-bold mb-4">The Vision</h2>
            <p className="text-[var(--text-secondary)] leading-relaxed">
              By leveraging the Google Gemini ADK and dynamic Model Context Protocol (MCP) generation, we are making the world's
              first truly self-expanding AI workspace. A system where developers spend zero time writing boilerplate API wrappers,
              and 100% of their time solving actual business problems.
            </p>
          </div>
        </div>

        {/* The Team */}
        <div className="mb-24">
          <h2 className="text-3xl md:text-4xl font-extrabold mb-12 text-center">Meet the Team</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-12">
            <div className="flex flex-col items-center">
              <Image src="/images/umang-vijay.png" alt="Umang Vijay" width={128} height={128} className="w-32 h-32 rounded-full object-cover object-top mb-6 shadow-xl" />
              <h3 className="text-xl font-bold">Umang Vijay</h3>
              <p className="text-[var(--accent)] font-medium mt-1">Co-Founder & CTO</p>
            </div>
            <div className="flex flex-col items-center">
              <Image src="/images/ashmit-rana.png" alt="Ashmit Rana" width={128} height={128} className="w-32 h-32 rounded-full object-cover object-top mb-6 shadow-xl" />
              <h3 className="text-xl font-bold">Ashmit Rana</h3>
              <p className="text-[var(--accent)] font-medium mt-1">Co-Founder & CEO</p>
            </div>
          </div>
        </div>

        {/* The Journey */}
        <div className="glass-card p-8 md:p-14 mb-20 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">The AgentOS Journey</h2>
          <p className="text-lg md:text-xl text-[var(--text-secondary)] leading-relaxed max-w-2xl mx-auto">
            Born out of a Google DevPost hackathon, AgentOS started as an ambitious idea to combine LangChain-style reasoning
            with enterprise-grade deterministic execution. Today, it stands as the most advanced autonomous workspace available,
            powered by Google Gemini.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/get-started" className="btn btn-primary btn-lg w-full sm:w-auto text-center">Try AgentOS Now</Link>
          <Link href="/features" className="btn btn-secondary btn-lg w-full sm:w-auto text-center">View Features</Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-12 px-6 md:py-16 md:px-10 border-t border-[var(--border-primary)] bg-[var(--bg-primary)] mt-12 md:mt-20">
        <div style={{ maxWidth: 1200, margin: "0 auto", textAlign: "center", color: "var(--text-secondary)" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12, marginBottom: 24 }}>
            <div style={{
              width: 24, height: 24, borderRadius: "6px",
              background: "linear-gradient(135deg, var(--accent), var(--accent-pink))",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12, fontWeight: 800, color: "white"
            }}>A</div>
            <span style={{ fontSize: 18, fontWeight: 800 }}>AgentOS</span>
          </div>
          <p>© 2026 AgentOS Inc. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
