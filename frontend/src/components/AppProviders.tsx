"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthProvider } from "@/lib/auth-context";
import { NetworkStatusProvider } from "@/hooks/NetworkStatusProvider";
import { ReactNode } from "react";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
const GOOGLE_ENABLED = Boolean(GOOGLE_CLIENT_ID) && GOOGLE_CLIENT_ID !== "dummy-client-id";

export function AppProviders({ children }: { children: ReactNode }) {
  const tree = (
    <AuthProvider>
      <NetworkStatusProvider />
      {children}
    </AuthProvider>
  );

  if (!GOOGLE_ENABLED) return tree;

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      {tree}
    </GoogleOAuthProvider>
  );
}
