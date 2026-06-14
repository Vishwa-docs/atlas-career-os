/**
 * Stream a chat completion from the backend over SSE.
 * We use fetch + ReadableStream (not EventSource) so we can send the auth
 * header and a JSON body. Calls `onToken` for each text delta.
 */

import { API_BASE_URL } from "./apiClient";
import { getTokens } from "./tokenStore";

export interface StreamChatOptions {
  path: string; // e.g. "/ai/coach/stream"
  body: unknown;
  onToken: (delta: string) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
  signal?: AbortSignal;
}

export async function streamChat({
  path,
  body,
  onToken,
  onDone,
  onError,
  signal,
}: StreamChatOptions) {
  try {
    const token = getTokens()?.access_token;
    const res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
      signal,
    });
    if (!res.ok || !res.body) {
      throw new Error(`Stream failed: ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";
      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (data === "[DONE]") {
          onDone?.();
          return;
        }
        try {
          const parsed = JSON.parse(data) as { delta?: string };
          if (parsed.delta) onToken(parsed.delta);
        } catch {
          onToken(data);
        }
      }
    }
    onDone?.();
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    onError?.(err as Error);
  }
}
