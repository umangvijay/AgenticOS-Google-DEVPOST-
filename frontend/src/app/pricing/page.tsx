import Link from "next/link";
import React from "react";
import PublicNavbar from "@/components/PublicNavbar";
import dynamic from "next/dynamic";

const TiltCard = dynamic(() => import("@/components/TiltCard"));

export default function PricingPage() {
  return (
    <div className="mesh-gradient">
      <PublicNavbar />

      <main className="py-12 px-4 md:py-20 md:px-8">
        <div className="max-w-6xl mx-auto pb-10 md:pb-20">
          <div className="text-center mb-16 md:mb-20 mt-6 md:mt-10">

            <h1 className="animate-fade-in-up text-4xl md:text-5xl lg:text-6xl font-black mb-6 text-[var(--text-primary)]">
              Simple, transparent pricing.
            </h1>
            <p className="animate-fade-in-up text-lg md:text-xl text-[var(--text-secondary)]" style={{ animationDelay: "0.1s" }}>
              Start for free, upgrade when you need more power.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-8 items-stretch">
            
            {/* Starter Plan */}
            <TiltCard className="glass-card pricing-card animate-fade-in-up p-6 md:p-10 flex flex-col" style={{ animationDelay: "0.2s" }}>
              <h2 className="text-xl md:text-2xl font-extrabold mb-2">Starter</h2>
              <p className="text-[var(--text-secondary)] mb-6">Perfect for individuals exploring automation.</p>
              <div className="text-4xl md:text-5xl font-extrabold mb-6">₹299<span className="text-base text-[var(--text-tertiary)] font-normal">/mo</span></div>
              <ul className="list-none p-0 mb-8 flex flex-col gap-3 flex-1 font-medium antialiased">
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> 100 Workflow runs/mo</li>
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> 5 Custom MCPs</li>
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> Community Support</li>
              </ul>
              <Link href="/signup" className="btn btn-secondary w-full mt-auto">Get Started</Link>
            </TiltCard>

            {/* Pro Plan */}
            <TiltCard className="glass-card pricing-card animate-fade-in-up p-6 md:p-10 flex flex-col relative border-2 border-[var(--accent)]" style={{ animationDelay: "0.3s", boxShadow: "0 20px 40px rgba(216, 133, 143, 0.15)", overflow: "visible" }}>
              <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-[var(--accent)] text-[#5c1621] px-4 py-1 rounded-full text-xs font-extrabold tracking-widest whitespace-nowrap">
                MOST POPULAR
              </div>
              <h2 className="text-xl md:text-2xl font-extrabold mb-2">Professional</h2>
              <p className="text-[var(--text-secondary)] mb-6">For teams building production AI workflows.</p>
              <div className="text-4xl md:text-5xl font-extrabold mb-6 text-[var(--accent)]">₹899<span className="text-base text-[var(--text-tertiary)] font-normal">/mo</span></div>
              <ul className="list-none p-0 mb-8 flex flex-col gap-3 flex-1 font-medium antialiased">
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> Unlimited Workflow runs</li>
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> Unlimited Custom MCPs</li>
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> GPT-4o & Claude 3.5 Sonnet Support</li>
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> Priority Email Support</li>
              </ul>
              <Link href="/signup" className="btn btn-primary w-full mt-auto text-center">Upgrade to Pro</Link>
            </TiltCard>

            {/* Enterprise Plan */}
            <TiltCard className="glass-card pricing-card animate-fade-in-up p-6 md:p-10 flex flex-col" style={{ animationDelay: "0.4s" }}>
              <h2 className="text-xl md:text-2xl font-extrabold mb-2">Enterprise</h2>
              <p className="text-[var(--text-secondary)] mb-6">Custom solutions for large organizations.</p>
              <div className="text-4xl md:text-5xl font-extrabold mb-6">₹1199<span className="text-base text-[var(--text-tertiary)] font-normal">/mo</span></div>
              <ul className="list-none p-0 mb-8 flex flex-col gap-3 flex-1 font-medium antialiased">
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> Dedicated Infrastructure</li>
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> VPC Peering & SOC2 Compliance</li>
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> Dedicated Success Manager</li>
                <li className="flex gap-2"><span className="text-[var(--success)]">✓</span> 99.99% Uptime SLA</li>
              </ul>
              <Link href="/contact" className="btn btn-secondary w-full mt-auto text-center">Contact Sales</Link>
            </TiltCard>

          </div>
        </div>
      </main>
    </div>
  );
}
