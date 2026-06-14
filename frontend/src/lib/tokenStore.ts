/** In-memory + localStorage token store, decoupled from React so the API client
 * can read tokens without importing the auth store (avoids a circular import). */

import type { TokenPair } from "@/types/api";

const KEY = "atlas.tokens";

let memory: TokenPair | null = null;
const listeners = new Set<(t: TokenPair | null) => void>();

function load(): TokenPair | null {
  if (memory) return memory;
  try {
    const raw = localStorage.getItem(KEY);
    memory = raw ? (JSON.parse(raw) as TokenPair) : null;
  } catch {
    memory = null;
  }
  return memory;
}

export function getTokens(): TokenPair | null {
  return load();
}

export function setTokens(tokens: TokenPair | null) {
  memory = tokens;
  try {
    if (tokens) localStorage.setItem(KEY, JSON.stringify(tokens));
    else localStorage.removeItem(KEY);
  } catch {
    /* ignore storage errors (private mode) */
  }
  listeners.forEach((l) => l(tokens));
}

export function clearTokens() {
  setTokens(null);
}

export function onTokenChange(cb: (t: TokenPair | null) => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}
