"use client";
import { useState } from "react";

export default function Dashboard() {
  const [goal, setGoal] = useState("");
  const [runData, setRunData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setRunData(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/v1/intent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal }),
      });
      const data = await response.json();
      setRunData(data);
    } catch (error) {
      console.error("Error executing goal:", error);
      setRunData({ status: "FAILED", result: { error: "Failed to connect to backend API." } });
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-black text-white p-8 font-sans">
      <div className="max-w-3xl mx-auto space-y-8">
        <header className="space-y-2">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
            AgentOS Workspace
          </h1>
          <p className="text-gray-400">Phase 1 End-to-End Vertical Slice</p>
        </header>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="What do you want AgentOS to do? (e.g. 'What time is it in UTC?')"
            className="w-full p-4 rounded-xl bg-gray-900 border border-gray-800 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 text-lg transition-all"
          />
          <button
            type="submit"
            disabled={loading || !goal}
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl font-semibold shadow-lg transition-all"
          >
            {loading ? "Executing Agents..." : "Start Agent"}
          </button>
        </form>

        {runData && (
          <div className="space-y-6 pt-8 border-t border-gray-800 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h2 className="text-2xl font-semibold">Execution Timeline</h2>
            
            <div className="bg-gray-900 p-6 rounded-xl space-y-4 border border-gray-800 shadow-xl">
              <div className="flex justify-between items-center pb-4 border-b border-gray-800">
                <span className="text-gray-400">Run ID</span>
                <span className="font-mono text-xs bg-gray-800 px-2 py-1 rounded">{runData.run_id || 'N/A'}</span>
              </div>
              
              <div className="flex justify-between items-center pb-4 border-b border-gray-800">
                <span className="text-gray-400">Status</span>
                <span className={`font-semibold px-3 py-1 rounded-full text-sm ${
                  runData.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' : 
                  runData.status === 'FAILED' ? 'bg-red-500/20 text-red-400' : 
                  'bg-yellow-500/20 text-yellow-400'
                }`}>
                  {runData.status}
                </span>
              </div>

              <div className="space-y-3 pt-2">
                <span className="text-gray-400 block">Agent Results:</span>
                <pre className="bg-black p-4 rounded-lg text-sm overflow-x-auto border border-gray-800 text-gray-300">
                  {JSON.stringify(runData.result, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
