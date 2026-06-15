import { Component, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  /** Changing this key resets the boundary (e.g. on route change). */
  resetKey?: string;
}
interface State {
  error: Error | null;
}

/**
 * Catches render errors in a subtree so one failing page can't blank the whole
 * app. Shows a friendly fallback; the rest of the shell (nav) stays usable.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidUpdate(prev: Props) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
          <div className="rounded-full bg-destructive/10 p-3">
            <AlertTriangle className="h-6 w-6 text-destructive" />
          </div>
          <div>
            <h2 className="font-display text-xl font-semibold">This view hit a snag</h2>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              Something went wrong rendering this page. The rest of Atlas is still
              working — try again or head back.
            </p>
            <p className="mt-2 font-mono text-xs text-muted-foreground/70">
              {this.state.error.message}
            </p>
          </div>
          <Button variant="outline" onClick={() => this.setState({ error: null })}>
            <RotateCcw className="h-4 w-4" /> Try again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
