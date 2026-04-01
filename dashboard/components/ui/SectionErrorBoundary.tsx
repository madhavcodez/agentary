"use client";

import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  /** Section name shown in the error fallback. */
  section?: string;
}

interface State {
  hasError: boolean;
}

/**
 * Lightweight error boundary for individual page sections.
 * Isolates crashes so the rest of the page stays interactive.
 */
export default class SectionErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="glass-card rounded-xl p-6 text-center">
          <p className="text-sm text-gray-400 mb-3">
            {this.props.section
              ? `Failed to load ${this.props.section}`
              : "This section encountered an error"}
          </p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
