/**
 * GlassBoxPanel — the universal "why" surface — must always render the
 * rationale and a human-readable confidence label. This is the trust contract:
 * Atlas never shows a black-box score, so the panel surfaces the reasoning,
 * evidence, what-would-change-this, and caveats every time.
 */

import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { GlassBoxPanel } from "@/components/glass-box";
import type { GlassBox } from "@/types/api";

function makeGlassBox(overrides: Partial<GlassBox> = {}): GlassBox {
  return {
    rationale:
      "Your recent analytics roles and strong SQL signal map closely to this position.",
    confidence: "medium",
    confidence_score: 0.62,
    citations: [
      { label: "Your career history", source_type: "career_history", snippet: "3y as Data Analyst" },
    ],
    what_would_change_this: ["More verified Python evidence would raise the fit."],
    caveats: ["Sub-scores use available profile data; gaps default to neutral."],
    ...overrides,
  };
}

describe("GlassBoxPanel", () => {
  it("renders the rationale text", () => {
    render(<GlassBoxPanel glassBox={makeGlassBox()} />);
    expect(
      screen.getByText(/recent analytics roles and strong SQL signal/i),
    ).toBeInTheDocument();
  });

  it("renders a human-readable confidence label with the score", () => {
    render(<GlassBoxPanel glassBox={makeGlassBox({ confidence: "medium", confidence_score: 0.62 })} />);
    // ConfidenceMeter maps medium -> "Moderate confidence" and formats 0.62 -> "62%".
    expect(screen.getByText(/Moderate confidence/i)).toBeInTheDocument();
    expect(screen.getByText(/62%/)).toBeInTheDocument();
  });

  it("maps a high confidence band to its label", () => {
    render(
      <GlassBoxPanel glassBox={makeGlassBox({ confidence: "high", confidence_score: 0.9 })} />,
    );
    expect(screen.getByText(/High confidence/i)).toBeInTheDocument();
  });

  it("surfaces citations, what-would-change-this, and caveats", () => {
    render(<GlassBoxPanel glassBox={makeGlassBox()} />);
    expect(screen.getByText("Your career history")).toBeInTheDocument();
    expect(screen.getByText(/More verified Python evidence/i)).toBeInTheDocument();
    expect(screen.getByText(/gaps default to neutral/i)).toBeInTheDocument();
  });
});
