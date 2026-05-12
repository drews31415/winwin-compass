import type { Metadata } from "next";
import { Settings } from "lucide-react";
import { DigitalCareModeToggle } from "@/components/layout/DigitalCareModeToggle";

export const metadata: Metadata = { title: "설정" };

export default function SettingsPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 p-8 text-center">
      <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-primary/10">
        <Settings className="h-8 w-8 text-brand-primary" />
      </span>
      <h1 className="text-2xl font-bold text-brand-text-main">설정</h1>
      <p className="max-w-sm text-sm text-brand-text-muted">
        디지털 약자 모드를 켜면 글씨와 입력창이 커지고, 주요 안내가 짧은 요약형 문장으로 표시됩니다.
      </p>
      <DigitalCareModeToggle />
      <p className="max-w-sm rounded-lg bg-white px-4 py-3 text-sm text-brand-text-muted shadow-card">
        채팅 화면의 마이크 버튼과 함께 사용하면 음성 입력과 큰 글씨 모드를 같이 시연할 수 있습니다.
      </p>
    </div>
  );
}
