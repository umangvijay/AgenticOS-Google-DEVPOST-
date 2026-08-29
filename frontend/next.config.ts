import type { NextConfig } from "next";
import fs from "fs";
import path from "path";
import withBundleAnalyzer from "@next/bundle-analyzer";

function loadRootEnv() {
  const envPath = path.join(__dirname, "..", ".env");
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 1) continue;
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (process.env[key] === undefined) process.env[key] = val;
  }
}
loadRootEnv();

const nextConfig: NextConfig = {
  output: "standalone",
  compress: true,
  devIndicators: false,
  experimental: {
    optimizePackageImports: ["lucide-react", "radash", "@xyflow/react"],
    optimizeCss: true,
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
          { key: "X-DNS-Prefetch-Control", value: "off" },
        ],
      },
      {
        source: "/images/(.*)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },
  webpack: (config, { dev, isServer }) => {
    // Forcefully disable core-js polyfills that Next.js aggressively injects
    if (!dev && !isServer) {
      config.resolve.alias = {
        ...config.resolve.alias,
        "core-js": false,
        "@swc/helpers": false,
        "next/dist/client/polyfills": false,
        "next/dist/build/polyfills/polyfill-nomodule": false,
        "next/dist/build/polyfills/polyfills": false,
      };
    }
    return config;
  },
};

const analyzer = withBundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

export default analyzer(nextConfig);
