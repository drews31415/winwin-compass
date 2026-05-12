"use client";

import type { ReactNode } from "react";
import { Component } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  children: ReactNode;
  fallback?: ReactNode;
};

type State = {
  hasError: boolean;
};

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    console.error("UI error:", error);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-brand-risk-high/20 bg-white p-8 text-center">
          <AlertTriangle className="mb-3 h-8 w-8 text-brand-risk-high" />
          <h2 className="text-lg font-bold text-brand-text-main">화면을 불러오지 못했습니다</h2>
          <p className="mt-1 text-sm text-brand-text-muted">잠시 후 다시 시도해 주세요.</p>
          <Button className="mt-4 bg-brand-primary hover:bg-brand-primary-dark" onClick={() => this.setState({ hasError: false })}>
            다시 시도
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
