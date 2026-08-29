import fs from "fs";
import path from "path";
import { NextResponse } from "next/server";

const BAD_WORDS = [
  "abusive", "spam", "idiot", "hate", "scam", "stupid",
  "crap", "dumb", "loser", "jerk", "moron", "trash", "fake", "phishing", "profanity"
];

const DEFAULT_POSTS = [
  {
    title: "Introducing AgentOS: the workspace that builds its own tools",
    date: "August 15, 2026",
    category: "Product",
    excerpt: "Tell AgentOS a goal. It plans, builds missing app integrations, and executes with live data — not a hardcoded catalog.",
  },
  {
    title: "How MCP creation works",
    date: "August 12, 2026",
    category: "Engineering",
    excerpt: "From an OpenAPI spec, docs URL, or a plain-language description, the factory normalizes, probes, and registers tools the agent can call immediately.",
  },
  {
    title: "Bring your own Gemini key",
    date: "August 10, 2026",
    category: "Guides",
    excerpt: "Store a Gemini API key in Vault as `gemini` and AgentOS will use your quota for planning, generation, and MCP builds.",
  },
];

function dataPaths() {
  return [
    path.join(process.cwd(), "data", "blogs.json"),
    path.join(process.cwd(), "frontend", "data", "blogs.json"),
  ];
}

function readBlogs() {
  for (const file of dataPaths()) {
    try {
      if (fs.existsSync(file)) {
        const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
        if (Array.isArray(parsed) && parsed.length) return parsed;
      }
    } catch (error) {
      console.error("Error reading blogs:", error);
    }
  }
  return DEFAULT_POSTS;
}

function writeBlogs(blogs: unknown[]) {
  const file = dataPaths()[0];
  const dir = path.dirname(file);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(file, JSON.stringify(blogs, null, 2));
}

export async function GET() {
  return NextResponse.json(readBlogs());
}

export async function POST(request: Request) {
  try {
    const auth = request.headers.get("authorization") || "";
    if (!auth.toLowerCase().startsWith("bearer ")) {
      return NextResponse.json({ error: "Authentication required" }, { status: 401 });
    }
    const api = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000/api/v1";
    const me = await fetch(`${api.replace(/\/$/, "")}/auth/me`, {
      headers: { Authorization: auth },
      cache: "no-store",
    });
    if (!me.ok) {
      return NextResponse.json({ error: "Invalid or expired session" }, { status: 401 });
    }

    const body = await request.json();
    const { title, category, excerpt } = body;
    if (!title || !category || !excerpt) {
      return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
    }
    const contentToScan = `${title} ${category} ${excerpt}`.toLowerCase();
    for (const badWord of BAD_WORDS) {
      if (contentToScan.includes(badWord)) {
        return NextResponse.json(
          { error: `Post rejected: contains restricted language ('${badWord}')` },
          { status: 400 }
        );
      }
    }
    const newBlog = {
      title,
      category,
      excerpt,
      date: new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }),
    };
    const updated = [newBlog, ...readBlogs()];
    writeBlogs(updated);
    return NextResponse.json(newBlog, { status: 201 });
  } catch {
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
