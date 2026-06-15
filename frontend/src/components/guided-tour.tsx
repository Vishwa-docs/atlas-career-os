/**
 * Guided product tour ("Qtips") — a spotlight walkthrough that steps a visitor
 * through the key features of whichever workspace they're in. Triggered from the
 * header; never auto-hijacks the screen. Each step can navigate to a route and
 * spotlight an element (found by CSS selector); if the element isn't present the
 * card simply centres itself.
 */

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface TourStep {
  /** Navigate here before showing the step. */
  route?: string;
  /** CSS selector of the element to spotlight (e.g. an a[href=...]). */
  selector?: string;
  title: string;
  body: string;
}

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PAD = 8;

export function GuidedTour({
  steps,
  open,
  onClose,
}: {
  steps: TourStep[];
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const frame = useRef<number | null>(null);

  const step = steps[index];

  const measure = useCallback(() => {
    if (!step?.selector) {
      setRect(null);
      return;
    }
    const el = document.querySelector(step.selector) as HTMLElement | null;
    if (!el) {
      setRect(null);
      return;
    }
    const r = el.getBoundingClientRect();
    setRect({ top: r.top, left: r.left, width: r.width, height: r.height });
    el.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [step]);

  // Reset to first step whenever the tour (re)opens.
  useEffect(() => {
    if (open) setIndex(0);
  }, [open]);

  // Navigate + poll for the target element (handles lazy route loads).
  useLayoutEffect(() => {
    if (!open || !step) return;
    let tries = 0;
    let timer: number;
    if (step.route) navigate(step.route);
    const tick = () => {
      measure();
      tries += 1;
      if (tries < 8) timer = window.setTimeout(tick, 140);
    };
    timer = window.setTimeout(tick, 120);
    return () => window.clearTimeout(timer);
  }, [open, index, step, navigate, measure]);

  // Keep the spotlight glued to the element on scroll/resize.
  useEffect(() => {
    if (!open) return;
    const onMove = () => {
      if (frame.current) cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(measure);
    };
    window.addEventListener("scroll", onMove, true);
    window.addEventListener("resize", onMove);
    return () => {
      window.removeEventListener("scroll", onMove, true);
      window.removeEventListener("resize", onMove);
    };
  }, [open, measure]);

  if (!open || !step) return null;

  const last = index === steps.length - 1;
  const first = index === 0;

  // Tooltip placement: below the target if it fits, else above, else centred.
  const vh = window.innerHeight;
  const vw = window.innerWidth;
  let cardStyle: React.CSSProperties;
  if (rect) {
    const below = rect.top + rect.height + 12;
    const placeBelow = below + 200 < vh;
    cardStyle = {
      position: "fixed",
      top: placeBelow ? below : Math.max(12, rect.top - 200),
      left: Math.min(Math.max(12, rect.left), vw - 360),
    };
  } else {
    cardStyle = { position: "fixed", top: "50%", left: "50%", transform: "translate(-50%,-50%)" };
  }

  return (
    <div className="fixed inset-0 z-[100]" role="dialog" aria-label="Guided tour">
      {/* Spotlight (or full dim if no target) */}
      {rect ? (
        <div
          className="pointer-events-none fixed rounded-lg ring-2 ring-brand transition-all duration-300"
          style={{
            top: rect.top - PAD,
            left: rect.left - PAD,
            width: rect.width + PAD * 2,
            height: rect.height + PAD * 2,
            boxShadow: "0 0 0 9999px rgba(2,6,23,0.66)",
          }}
        />
      ) : (
        <div className="fixed inset-0 bg-slate-950/66" />
      )}

      {/* Card */}
      <div
        style={cardStyle}
        className={cn(
          "w-[340px] max-w-[calc(100vw-24px)] rounded-xl border bg-popover p-5 text-popover-foreground shadow-2xl",
          "animate-in fade-in-0 zoom-in-95",
        )}
      >
        <div className="mb-2 flex items-center justify-between">
          <span className="text-[0.65rem] font-semibold uppercase tracking-widest text-brand">
            Tour · {index + 1} / {steps.length}
          </span>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
            aria-label="End tour"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <h3 className="font-display text-lg font-semibold">{step.title}</h3>
        <p className="mt-1.5 text-sm text-muted-foreground">{step.body}</p>
        <div className="mt-4 flex items-center justify-between">
          <button onClick={onClose} className="text-xs text-muted-foreground hover:underline">
            Skip tour
          </button>
          <div className="flex gap-2">
            {!first && (
              <Button variant="outline" size="sm" onClick={() => setIndex((i) => i - 1)}>
                <ArrowLeft /> Back
              </Button>
            )}
            <Button
              variant="brand"
              size="sm"
              onClick={() => (last ? onClose() : setIndex((i) => i + 1))}
            >
              {last ? "Done" : "Next"}
              {!last && <ArrowRight />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
