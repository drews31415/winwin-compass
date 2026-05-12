import type { Metadata } from "next";
import { Settings } from "lucide-react";

export const metadata: Metadata = { title: "설정" };

export default function SettingsPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8 text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-golmok-primary/10">
        <Settings className="h-8 w-8 text-golmok-primary" />
      </span>
      <h1 className="text-2xl font-bold text-golmok-text-main">설정</h1>
      <p className="max-w-sm text-sm text-golmok-text-muted">
        앱 설정 기능을 준비 중입니다.
      </p>
    </div>
  );
}
