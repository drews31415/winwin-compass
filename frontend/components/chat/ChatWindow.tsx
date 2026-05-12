"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";
import type { Message } from "@/lib/hooks/useChat";

const INTENT_LABEL: Record<string, string> = {
  data_query:  "데이터 분석",
  report:      "상권 리포트",
  policy:      "지원 정책",
  comparison:  "상권 비교",
  general:     "일반 상담",
};

interface Props {
  messages: Message[];
}

function StreamingCursor() {
  return (
    <span
      className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-brand-primary align-middle"
      aria-hidden="true"
    />
  );
}

function IntentBadge({ intent }: { intent: string }) {
  const label = INTENT_LABEL[intent] ?? intent;
  return (
    <span className="mb-1 inline-block rounded-full bg-brand-primary/10 px-2.5 py-0.5 text-[10px] font-medium text-brand-primary">
      {label}
    </span>
  );
}

function UserBubble({ message }: { message: Message }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[75%]">
        <div className="chat-bubble-user">{message.content}</div>
        <p className="mt-1 text-right text-[10px] text-gray-400">
          {message.timestamp.toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

function AssistantBubble({ message }: { message: Message }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        {message.intent && !message.isStreaming && (
          <IntentBadge intent={message.intent} />
        )}
        <div className={cn("chat-bubble-ai", message.isStreaming && "min-h-[2rem]")}>
          {message.content ? (
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="mb-2 list-disc pl-4">{children}</ul>,
                ol: ({ children }) => <ol className="mb-2 list-decimal pl-4">{children}</ol>,
                li: ({ children }) => <li className="mb-0.5">{children}</li>,
                h3: ({ children }) => (
                  <h3 className="mb-1.5 mt-3 font-semibold text-brand-text-main first:mt-0">
                    {children}
                  </h3>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="mb-2 border-l-2 border-brand-primary/40 pl-3 text-sm text-gray-500">
                    {children}
                  </blockquote>
                ),
                code: ({ children, className }) => {
                  const isBlock = className?.includes("language-");
                  return isBlock ? (
                    <pre className="mb-2 overflow-x-auto rounded-lg bg-gray-900 px-4 py-3 text-xs text-gray-100">
                      <code>{children}</code>
                    </pre>
                  ) : (
                    <code className="rounded bg-gray-100 px-1 py-0.5 text-xs text-gray-800">
                      {children}
                    </code>
                  );
                },
                strong: ({ children }) => (
                  <strong className="font-semibold text-brand-text-main">{children}</strong>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : (
            <span className="text-gray-400">생각 중...</span>
          )}
          {message.isStreaming && <StreamingCursor />}
        </div>
        {!message.isStreaming && (
          <p className="mt-1 text-[10px] text-gray-400">
            {message.timestamp.toLocaleTimeString("ko-KR", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
      </div>
    </div>
  );
}

export function ChatWindow({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col gap-4 px-4 py-4">
      {messages.map((msg) =>
        msg.role === "user" ? (
          <UserBubble key={msg.id} message={msg} />
        ) : (
          <AssistantBubble key={msg.id} message={msg} />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}
