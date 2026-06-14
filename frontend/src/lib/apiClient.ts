/**
 * Typed fetch client with automatic bearer-token injection and transparent
 * refresh-on-401 (single-flight). Throws `ApiClientError` with the backend's
 * normalized error shape so callers/UI can show meaningful messages.
 */

import type { ApiError, TokenPair } from "@/types/api";
import { clearTokens, getTokens, setTokens } from "./tokenStore";

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api/v1";

export class ApiClientError extends Error {
  code: string;
  status: number;
  details?: unknown;
  constructor(status: number, body: ApiError | undefined, fallback: string) {
    super(body?.error?.message ?? fallback);
    this.code = body?.error?.code ?? "error";
    this.status = status;
    this.details = body?.error?.details;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
  auth?: boolean; // default true
  signal?: AbortSignal;
  formUrlEncoded?: boolean;
}

let refreshing: Promise<TokenPair | null> | null = null;

async function doRefresh(): Promise<TokenPair | null> {
  const tokens = getTokens();
  if (!tokens?.refresh_token) return null;
  const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!res.ok) {
    clearTokens();
    return null;
  }
  const next = (await res.json()) as TokenPair;
  setTokens(next);
  return next;
}

function buildUrl(path: string, params?: RequestOptions["params"]) {
  const url = new URL(
    `${API_BASE_URL}${path}`,
    typeof window !== "undefined" ? window.location.origin : "http://localhost",
  );
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    }
  }
  return url.toString().replace(/^http:\/\/localhost(?=\/)/, "");
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, auth = true, signal, formUrlEncoded } = opts;

  const exec = async (token?: string): Promise<Response> => {
    const headers: Record<string, string> = {};
    let payload: BodyInit | undefined;
    if (formUrlEncoded && body && typeof body === "object") {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      payload = new URLSearchParams(body as Record<string, string>).toString();
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
    if (auth && token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(buildUrl(path, params), { method, headers, body: payload, signal });
  };

  let token = auth ? getTokens()?.access_token : undefined;
  let res = await exec(token);

  if (res.status === 401 && auth && getTokens()?.refresh_token) {
    refreshing = refreshing ?? doRefresh();
    const refreshed = await refreshing;
    refreshing = null;
    if (refreshed) {
      token = refreshed.access_token;
      res = await exec(token);
    }
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;

  if (!res.ok) {
    throw new ApiClientError(res.status, data as ApiError, res.statusText);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, params?: RequestOptions["params"], opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "GET", params }),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "POST", body }),
  put: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "PUT", body }),
  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "PATCH", body }),
  delete: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "DELETE" }),
};
