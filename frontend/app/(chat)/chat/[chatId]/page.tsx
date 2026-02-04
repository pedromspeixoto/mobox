import { Suspense } from "react";
import { redirect } from "next/navigation";
import type { ChatMessage } from "@/lib/types";
import { getMessages, getChatContext } from "@/app/(chat)/actions/sessions";
import { LoadingSpinner } from "@/components/ui/spinner";
import { ChatClient } from "@/app/(chat)/chat/[chatId]/chat-client";

interface ChatPageContentProps {
  chatId: string;
}

async function ChatPageContent({ chatId }: ChatPageContentProps) {
  // Fetch messages and context in parallel
  const [messagesResult, contextResult] = await Promise.all([
    getMessages(chatId, 30, 0),
    getChatContext(chatId),
  ]);

  // If context fetch failed (session doesn't exist), redirect to home
  if (!contextResult.success) {
    console.error(
      `Chat session ${chatId} not found (${contextResult.code || "error"}): ${contextResult.error}`
    );
    redirect("/");
  }

  // Get agent info from session context
  const agentId = contextResult.data.agent_id;
  const agentName = contextResult.data.agent_name;

  // Transform messages
  let initialMessages: ChatMessage[] = [];
  let paginationInfo = { total: 0, hasMore: false, offset: 0 };

  if (messagesResult.success) {
    initialMessages = messagesResult.data.messages.map((msg) => {
      const parts: ChatMessage["parts"] = [];

      // Add processing/status as reasoning part (if present in metadata)
      const processing = msg.metadata?.processing as string[] | undefined;
      if (processing && processing.length > 0) {
        parts.push({
          type: "reasoning" as const,
          text: processing.join("\n"),
          providerMetadata: { mobox: { variant: "processing" } },
        });
      }

      // Add todos as reasoning part (if present in metadata - persisted from stream)
      const todos = msg.metadata?.todos as Array<{ content: string; status?: string }> | undefined;
      if (todos && Array.isArray(todos) && todos.length > 0) {
        parts.push({
          type: "reasoning" as const,
          text: JSON.stringify(todos),
          providerMetadata: { mobox: { variant: "todos" } },
        });
      }

      // Add thinking as reasoning part (if present in metadata)
      const thinking = msg.metadata?.thinking as string | undefined;
      if (thinking) {
        parts.push({
          type: "reasoning" as const,
          text: thinking,
          providerMetadata: { mobox: { variant: "thinking" } },
        });
      }

      // Add text content
      if (msg.content) {
        parts.push({ type: "text" as const, text: msg.content });
      }

      return {
        id: msg.id,
        role: msg.role as "user" | "assistant",
        parts,
      };
    });

    paginationInfo = {
      total: messagesResult.data.total,
      hasMore: messagesResult.data.has_more,
      offset: messagesResult.data.offset,
    };
  }

  return (
    <ChatClient
      id={chatId}
      initialMessages={initialMessages}
      initialPagination={paginationInfo}
      agentId={agentId}
      agentName={agentName}
    />
  );
}

export default async function Page({
  params,
}: {
  params: Promise<{ chatId: string }>;
}) {
  const { chatId } = await params;

  return (
    <Suspense
      fallback={
        <div className="flex h-dvh items-center justify-center">
          <LoadingSpinner size="lg" />
        </div>
      }
    >
      <ChatPageContent chatId={chatId} />
    </Suspense>
  );
}
