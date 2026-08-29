"use client";
import { useNetworkStatus } from "./useNetworkStatus";

export function NetworkStatusProvider() {
  useNetworkStatus();
  return null;
}
