/**
 * Notifications: REST hooks + a realtime WebSocket subscription.
 *
 * The list/unread-count come over REST (authoritative). The WebSocket pushes a
 * lightweight hint the moment a notification is created, which we use to pop a
 * toast and invalidate the query so the bell updates instantly — no polling.
 */

import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, API_BASE_URL } from "@/lib/apiClient";
import { getTokens } from "@/lib/tokenStore";
import type { Paginated } from "@/types/api";

export interface AppNotification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  body: string | null;
  link: string | null;
  is_read: boolean;
  payload: Record<string, unknown>;
  created_at: string;
}

const KEY = ["notifications"] as const;

export function useNotifications() {
  return useQuery({
    queryKey: KEY,
    queryFn: () => api.get<Paginated<AppNotification>>("/notifications", { page_size: 30 }),
    refetchOnWindowFocus: true,
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.patch(`/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.patch("/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

/** Build the ws(s):// URL for the notifications channel from the REST base. */
function buildWsUrl(token: string): string {
  const base = API_BASE_URL;
  let httpUrl: string;
  if (/^https?:\/\//i.test(base)) {
    httpUrl = `${base}/notifications/ws`;
  } else {
    // Relative base (dev): go through the Vite proxy on the current origin.
    httpUrl = `${window.location.origin}${base}/notifications/ws`;
  }
  const url = new URL(httpUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("token", token);
  return url.toString();
}

/**
 * Subscribe to realtime notifications for the session. Mount once (in AppShell).
 * Auto-reconnects with backoff; tears down on unmount.
 */
export function useNotificationsRealtime() {
  const qc = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const closedRef = useRef(false);

  useEffect(() => {
    closedRef.current = false;

    const connect = () => {
      const token = getTokens()?.access_token;
      if (!token || closedRef.current) return;

      const ws = new WebSocket(buildWsUrl(token));
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
      };
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as {
            type: string;
            title?: string;
            body?: string;
            link?: string;
          };
          if (msg.type === "notification") {
            qc.invalidateQueries({ queryKey: KEY });
            toast(msg.title ?? "New notification", {
              description: msg.body ?? undefined,
            });
          }
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onclose = () => {
        if (closedRef.current) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, 15000);
        retryRef.current += 1;
        setTimeout(connect, delay);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closedRef.current = true;
      wsRef.current?.close();
    };
  }, [qc]);
}
