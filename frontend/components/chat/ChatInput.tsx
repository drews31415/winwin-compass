"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Send, Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";

const MAX_CHARS = 500;

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
  initialValue?: string;
}

export function ChatInput({ onSend, disabled = false, initialValue = "" }: Props) {
  const [text, setText] = useState(initialValue);
  const [listening, setListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (initialValue) setText(initialValue);
  }, [initialValue]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [text]);

  const handleSend = useCallback(() => {
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
  }, [text, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleVoice = useCallback(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const w = window as any;
    const SR = w.SpeechRecognition ?? w.webkitSpeechRecognition;

    if (!SR) {
      alert("이 브라우저는 음성 입력을 지원하지 않습니다.");
      return;
    }

    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }

    const rec = new SR() as any;
    rec.lang = "ko-KR";
    rec.interimResults = false;
    rec.maxAlternatives = 1;

    rec.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript;
      setText((prev) => (prev ? `${prev} ${transcript}` : transcript).slice(0, MAX_CHARS));
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);

    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  }, [listening]);

  const remaining = MAX_CHARS - text.length;
  const isOverLimit = remaining < 0;

  return (
    <div
      className={cn(
        "flex items-end gap-2 rounded-2xl border bg-white p-2 shadow-card",
        "transition-all duration-200",
        "focus-within:border-brand-primary focus-within:ring-2 focus-within:ring-brand-primary/15",
        disabled ? "opacity-60" : "border-gray-200",
      )}
    >
      {/* Voice button */}
      <div className="flex shrink-0 flex-col items-center gap-1">
        <button
          type="button"
          onClick={toggleVoice}
          disabled={disabled}
          className={cn(
            "rounded-xl p-2 transition-colors",
            listening
              ? "bg-red-100 text-red-500 hover:bg-red-200"
              : "text-gray-400 hover:bg-gray-100 hover:text-gray-600",
          )}
          aria-label={listening ? "음성 입력 중지" : "음성 입력 시작"}
        >
          {listening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </button>
        {listening && <span className="text-[10px] font-bold text-red-500">듣는 중</span>}
      </div>

      {/* Textarea */}
      <div className="relative flex flex-1 flex-col">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value.slice(0, MAX_CHARS))}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder="상권이나 창업에 대해 질문해 보세요 (Enter로 전송)"
          className={cn(
            "w-full resize-none bg-transparent py-2 pl-1 pr-2 text-sm text-gray-800",
            "placeholder:text-gray-400 focus:outline-none",
            "max-h-40 overflow-y-auto",
          )}
        />
        {/* Char count — only show when close to limit */}
        {remaining <= 100 && (
          <span
            className={cn(
              "self-end text-[10px]",
              isOverLimit ? "text-red-500" : "text-gray-400",
            )}
          >
            {text.length}/{MAX_CHARS}
          </span>
        )}
      </div>

      {/* Send button */}
      <button
        type="button"
        onClick={handleSend}
        disabled={disabled || !text.trim() || isOverLimit}
        className={cn(
          "shrink-0 rounded-xl p-2.5 transition-colors",
          "bg-brand-primary text-white",
          "hover:bg-brand-primary-dark",
          "disabled:cursor-not-allowed disabled:opacity-40",
        )}
        aria-label="메시지 전송"
      >
        <Send className="h-4 w-4" />
      </button>
    </div>
  );
}
