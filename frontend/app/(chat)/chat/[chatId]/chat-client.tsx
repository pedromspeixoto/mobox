"use client";

import dynamic from "next/dynamic";
import type { ChatMessage } from "@/lib/types";
import { LoadingSpinner } from "@/components/ui/spinner";

const Chat = dynamic(
  () => import("@/components/chat").then((m) => ({ default: m.Chat })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-dvh items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    ),
  }
);

interface ChatClientProps {
  id: string;
  initialMessages: ChatMessage[];
  initialPagination?: { total: number; hasMore: boolean; offset: number };
  agentId?: string | null;
  agentName?: string | null;
}

export function ChatClient({
  id,
  initialMessages,
  initialPagination,
  agentId,
  agentName,
}: ChatClientProps) {
  return (
    <Chat
      id={id}
      initialMessages={initialMessages}
      initialPagination={initialPagination}
      agentId={agentId}
      agentName={agentName}
      key={id}
    />
  );
}
