"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { submitGoal, listApprovals, ApprovalRequest } from "@/lib/api";
import { Play, Activity, Clock, CheckCircle, ShieldAlert } from "lucide-react";

export default function Dashboard() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const pendingApprovals = await listApprovals();
      setApprovals(pendingApprovals);
    } catch (err) {
      console.error("Failed to load dashboard data", err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;
    
    setLoading(true);
    setError("");
    try {
      const response = await submitGoal(goal);
      if (response.run_id) {
        router.push(`/workflow/${response.run_id}`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to submit goal");
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 p-6 lg:p-12 space-y-12">
      {/* Hero Input Section */}
      <section className="max-w-4xl mx-auto space-y-6 text-center">
        <h2 className="text-4xl lg:text-5xl font-extrabold tracking-tight">
          What can <span className="bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">AgenticOS</span> do for you?
        </h2>
        
        <form onSubmit={handleSubmit} className="relative group">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-500"></div>
          <div className="relative flex items-center bg-card border border-border rounded-2xl shadow-2xl overflow-hidden glass">
            <input
              type="text"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="e.g. 'Deploy a new staging environment' or 'Analyze recent security logs'"
              className="w-full px-6 py-5 bg-transparent border-none focus:outline-none focus:ring-0 text-lg lg:text-xl placeholder:text-muted-foreground"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !goal.trim()}
              className="m-2 px-6 py-3 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl font-semibold transition-all flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>Execute</span>
                  <Play className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
          {error && <p className="text-destructive mt-3 text-sm text-left px-2">{error}</p>}
        </form>
      </section>

      {/* Dashboard Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto">
        
        <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-3 text-muted-foreground">
            <ShieldAlert className="w-5 h-5 text-amber-500" />
            <h3 className="font-semibold text-foreground">Pending Approvals</h3>
          </div>
          <div className="space-y-3">
            {approvals.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">No pending actions require your approval.</p>
            ) : (
              approvals.map(app => (
                <div key={app.approval_id} className="p-3 bg-background rounded-lg border border-border text-sm flex justify-between items-center cursor-pointer hover:border-primary transition-colors" onClick={() => router.push(`/workflow/${app.run_id}`)}>
                  <div>
                    <p className="font-medium truncate">{app.tool_name}</p>
                    <p className="text-xs text-muted-foreground">Risk: {app.risk_level}</p>
                  </div>
                  <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-3 text-muted-foreground">
            <Activity className="w-5 h-5 text-blue-500" />
            <h3 className="font-semibold text-foreground">Active Workflows</h3>
          </div>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground italic">No active workflows running.</p>
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-3 text-muted-foreground">
            <Clock className="w-5 h-5 text-indigo-500" />
            <h3 className="font-semibold text-foreground">Recent Runs</h3>
          </div>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground italic">No recent run history.</p>
          </div>
        </div>

      </section>
    </div>
  );
}
