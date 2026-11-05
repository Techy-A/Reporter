import { Component, type ReactNode } from "react";

/** Shows a recoverable message instead of a blank page if a screen crashes. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div style={{ display: "grid", placeItems: "center", minHeight: "100%", padding: 24 }}>
        <div className="card" style={{ padding: 24, maxWidth: 420, display: "grid", gap: 12 }}>
          <h2>This screen hit a problem</h2>
          <p className="muted">Your data is safe. Reload the page to continue.</p>
          <button className="btn btn-primary" onClick={() => location.reload()}>Reload</button>
        </div>
      </div>
    );
  }
}
