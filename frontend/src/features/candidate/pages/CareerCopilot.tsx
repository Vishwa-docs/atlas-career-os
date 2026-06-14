import { useEffect, useRef, useState } from "react";
import { ArrowUp, Bot, Sparkles, Square, UserRound } from "lucide-react";
import { PageHeader } from "@/components/common";
import { GlassBoxPanel } from "@/components/glass-box";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { streamChat } from "@/lib/sse";
import { cn } from "@/lib/utils";
import { useAuth } from "@/stores/auth";
import type { GlassBox } from "@/types/api";

interface Turn {
  id: string;
  role: "user" | "assistant";
  content: string;
  glass_box?: GlassBox;
  streaming?: boolean;
}

const SUGGESTED = [
  "Am I underpaid for my role?",
  "What should I learn next to grow?",
  "Help me pivot into product management",
  "How do I explain a 1-year career break?",
];

export default function CareerCopilot() {
  const user = useAuth((s) => s.user);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  useEffect(() => () => abortRef.current?.abort(), []);

  function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || streaming) return;

    const history = turns.map((t) => ({ role: t.role, content: t.content }));
    const userTurn: Turn = { id: crypto.randomUUID(), role: "user", content: trimmed };
    const assistantId = crypto.randomUUID();
    const assistantTurn: Turn = {
      id: assistantId,
      role: "assistant",
      content: "",
      streaming: true,
    };
    setTurns((prev) => [...prev, userTurn, assistantTurn]);
    setInput("");
    setStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    void streamChat({
      path: "/ai/coach/stream",
      body: { message: trimmed, history },
      signal: controller.signal,
      onToken: (delta) => {
        setTurns((prev) =>
          prev.map((t) => (t.id === assistantId ? { ...t, content: t.content + delta } : t)),
        );
      },
      onDone: () => {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === assistantId
              ? {
                  ...t,
                  streaming: false,
                  content: t.content || "I'm not sure how to answer that yet.",
                }
              : t,
          ),
        );
        setStreaming(false);
        abortRef.current = null;
      },
      onError: () => {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === assistantId
              ? {
                  ...t,
                  streaming: false,
                  content:
                    t.content ||
                    "Sorry — I lost the connection. Please try asking that again.",
                }
              : t,
          ),
        );
        setStreaming(false);
        abortRef.current = null;
      },
    });
  }

  function stop() {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setTurns((prev) => prev.map((t) => (t.streaming ? { ...t, streaming: false } : t)));
  }

  return (
    <div className="animate-fade-in flex h-[calc(100vh-7rem)] flex-col">
      <PageHeader
        eyebrow="Signature · Career Copilot"
        title="Your AI career coach"
        description="Ask anything about your trajectory, pay, skills, or next move. Every answer shows its reasoning."
      />

      <div
        ref={scrollRef}
        className="flex-1 space-y-5 overflow-y-auto rounded-2xl border bg-card/40 p-4 sm:p-6"
      >
        {turns.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 rounded-2xl bg-gradient-to-br from-primary to-brand p-3 shadow-lg shadow-primary/30">
              <Bot className="h-7 w-7 text-primary-foreground" />
            </div>
            <h3 className="font-display text-xl font-semibold">How can I help you grow?</h3>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              I know your Career Graph — your history, skills, and the market. Ask me anything.
            </p>
            <div className="mt-6 grid w-full max-w-lg gap-2 sm:grid-cols-2">
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => send(s)}
                  className="rounded-xl border bg-card px-4 py-3 text-left text-sm shadow-sm transition-colors hover:border-brand/40 hover:bg-accent/40"
                >
                  <Sparkles className="mb-1.5 h-4 w-4 text-brand" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          turns.map((t) => <Bubble key={t.id} turn={t} userName={user?.full_name ?? "You"} />)
        )}
      </div>

      <form
        className="mt-4 flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
          placeholder="Ask your career coach…"
          rows={1}
          className="max-h-40 min-h-[2.75rem] resize-none"
        />
        {streaming ? (
          <Button type="button" variant="outline" size="icon" className="h-11 w-11" onClick={stop}>
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            type="submit"
            variant="brand"
            size="icon"
            className="h-11 w-11"
            disabled={!input.trim()}
          >
            <ArrowUp className="h-4 w-4" />
          </Button>
        )}
      </form>
    </div>
  );
}

function Bubble({ turn, userName }: { turn: Turn; userName: string }) {
  const isUser = turn.role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-muted text-foreground" : "bg-gradient-to-br from-primary to-brand text-primary-foreground",
        )}
      >
        {isUser ? <UserRound className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className={cn("min-w-0 max-w-[85%] space-y-2", isUser && "items-end text-right")}>
        <div
          className={cn(
            "inline-block whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser ? "bg-primary text-primary-foreground" : "border bg-card",
          )}
        >
          <span className="sr-only">{isUser ? userName : "Coach"}: </span>
          {turn.content}
          {turn.streaming && (
            <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-brand align-middle" />
          )}
        </div>
        {!isUser && turn.glass_box && !turn.streaming && (
          <GlassBoxPanel glassBox={turn.glass_box} defaultOpen={false} className="text-left" />
        )}
      </div>
    </div>
  );
}
