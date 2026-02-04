"use client";

import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport } from "ai";
import { useSearchParams, usePathname } from "next/navigation";
import { useEffect, useState, useRef, useCallback } from "react";
import { useChatSessions } from "@/contexts/chat-sessions-context";
import type { Attachment, ChatMessage } from "@/lib/types";
import type { AppUsage } from "@/lib/usage";
import { generateUUID } from "@/lib/utils/messages";
import { getMessages, getChatContext } from "@/app/(chat)/actions/sessions";
import {
  paginatedMessagesResponseSchema,
  type ChatMessage as BackendMessage,
} from "@/app/(chat)/actions/types";
import { useDataStream } from "@/components/data-stream-provider";
import { Messages } from "@/components/messages";
import { MultimodalInput } from "@/components/multimodal-input";
import { toast } from "@/components/toast";

export function Chat({
  id,
  initialMessages,
  initialPagination,
  agentId,
  agentName,
}: {
  id: string;
  initialMessages: ChatMessage[];
  initialPagination?: { total: number; hasMore: boolean; offset: number };
  agentId?: string | null;
  agentName?: string | null;
}) {
  const { setDataStream } = useDataStream();
  const { updateSession, refreshSessions } = useChatSessions();
  const pathname = usePathname();

  // Store chat ID in ref to prevent loss on errors
  const chatIdRef = useRef<string>(id);
  const expectedPathRef = useRef<string>(`/chat/${id}`);

  // Update ref if id changes (shouldn't happen, but defensive)
  useEffect(() => {
    chatIdRef.current = id;
    expectedPathRef.current = `/chat/${id}`;
  }, [id]);

  // Protect URL from being stripped - ensure we stay on the chat page
  useEffect(() => {
    const checkUrl = () => {
      if (pathname && pathname !== expectedPathRef.current) {
        // Restore correct URL without causing navigation
        window.history.replaceState(null, "", expectedPathRef.current);
      }
    };

    // Check immediately
    checkUrl();

    // Check periodically during chat lifecycle
    const interval = setInterval(checkUrl, 1000);

    return () => clearInterval(interval);
  }, [pathname]);

  const [input, setInput] = useState<string>("");
  const [usage, setUsage] = useState<AppUsage | undefined>();
  const [pagination, setPagination] = useState(
    initialPagination || { total: 0, hasMore: false, offset: 0 }
  );
  const [loadingMore, setLoadingMore] = useState(false);
  const [isFirstMessage, setIsFirstMessage] = useState(initialMessages.length === 0);

  // Fetch initial usage data for existing chats
  useEffect(() => {
    const fetchInitialUsage = async () => {
      // Only fetch if this is an existing chat with messages
      if (initialMessages.length === 0) return;

      const result = await getChatContext(id);

      if (result.success && (result.data.total_tokens > 0 || result.data.total_cost_usd > 0)) {
        setUsage({
          inputTokens: result.data.total_input_tokens,
          outputTokens: result.data.total_output_tokens,
          totalTokens: result.data.total_tokens,
          costUSD: {
            totalUSD: result.data.total_cost_usd,
          },
          context: {
            totalMax: result.data.context_window,
          },
          modelId: result.data.agent_id,
        });
      }
    };

    fetchInitialUsage();
  }, [id, initialMessages.length]);

  const {
    messages,
    setMessages,
    sendMessage,
    status,
    stop,
    regenerate,
  } = useChat<ChatMessage>({
    id,
    messages: initialMessages,
    experimental_throttle: 100,
    generateId: generateUUID,
    resume: true,
    transport: new DefaultChatTransport({
      api: "/api/chat",
      prepareReconnectToStreamRequest: ({ id }) => ({
        api: `/api/chat/${id}/stream`,
      }),
      prepareSendMessagesRequest(request) {
        // Only include agentId for new sessions (no initial messages)
        // For existing sessions, backend fetches agent from database
        const isNewSession = initialMessages.length === 0;

        return {
          body: {
            id: chatIdRef.current,
            message: request.messages.at(-1),
            ...(isNewSession && { agentId: agentId || "hello-world" }),
            ...request.body,
          },
        };
      },
    }),
    onData: (dataPart) => {
      setDataStream((ds) => (ds ? [...ds, dataPart] : []));
      if (dataPart.type === "data-usage") {
        const newUsage = dataPart.data as AppUsage;
        // Accumulate usage data across messages
        setUsage((prevUsage) => {
          if (!prevUsage) {
            return {
              ...newUsage,
              context: newUsage.context ?? { totalMax: 128000 },
            };
          }

          return {
            ...newUsage,
            inputTokens:
              (prevUsage.inputTokens ?? 0) + (newUsage.inputTokens ?? 0),
            outputTokens:
              (prevUsage.outputTokens ?? 0) + (newUsage.outputTokens ?? 0),
            totalTokens:
              (prevUsage.totalTokens ?? 0) + (newUsage.totalTokens ?? 0),
            cachedInputTokens:
              (prevUsage.cachedInputTokens ?? 0) +
              (newUsage.cachedInputTokens ?? 0),
            reasoningTokens:
              (prevUsage.reasoningTokens ?? 0) +
              (newUsage.reasoningTokens ?? 0),
            costUSD: {
              cacheReadUSD:
                (prevUsage.costUSD?.cacheReadUSD ?? 0) +
                (newUsage.costUSD?.cacheReadUSD ?? 0),
              inputUSD:
                (prevUsage.costUSD?.inputUSD ?? 0) +
                (newUsage.costUSD?.inputUSD ?? 0),
              outputUSD:
                (prevUsage.costUSD?.outputUSD ?? 0) +
                (newUsage.costUSD?.outputUSD ?? 0),
              reasoningUSD:
                (prevUsage.costUSD?.reasoningUSD ?? 0) +
                (newUsage.costUSD?.reasoningUSD ?? 0),
              totalUSD:
                (prevUsage.costUSD?.totalUSD ?? 0) +
                (newUsage.costUSD?.totalUSD ?? 0),
            },
            context: newUsage.context ?? prevUsage.context,
          };
        });
      }
    },
    onFinish: () => {
      if (isFirstMessage) {
        setIsFirstMessage(false);
        // Fallback: refetch sessions in case optimistic update missed (e.g. session not in list yet)
        refreshSessions();
      }
    },
    onError: (error) => {
      console.error("Chat error:", error);

      // Show error toast
      toast({
        type: "error",
        description: "Something went wrong. Please try again later.",
      });

      stop();
    },
  });

  // Wrap sendMessage to optimistically update sidebar title when first message is sent
  const sendMessageWithTitleUpdate = useCallback(
    (message: Parameters<typeof sendMessage>[0]) => {
      if (isFirstMessage && message && "parts" in message && message.parts) {
        const textParts = message.parts
          .filter((p): p is { type: "text"; text: string } => p.type === "text")
          .map((p) => p.text);
        const prompt = textParts.join("\n");
        if (prompt.trim()) {
          const title =
            prompt.length > 50 ? `${prompt.slice(0, 50)}...` : prompt;
          updateSession(id, { title });
        }
      }
      return sendMessage(message);
    },
    [sendMessage, isFirstMessage, id, updateSession]
  );

  const searchParams = useSearchParams();
  const query = searchParams.get("query");
  const [hasAppendedQuery, setHasAppendedQuery] = useState(false);

  useEffect(() => {
    if (query && !hasAppendedQuery) {
      sendMessageWithTitleUpdate({
        role: "user" as const,
        parts: [{ type: "text", text: query }],
      });

      setHasAppendedQuery(true);
      window.history.replaceState({}, "", `/chat`);
    }
  }, [query, sendMessageWithTitleUpdate, hasAppendedQuery]);

  const votes = undefined;

  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setDataStream([]);
  }, [id, setDataStream]);

  // Load more messages when scrolling to top
  const loadMoreMessages = useCallback(async () => {
    if (loadingMore || !pagination.hasMore) return;

    try {
      setLoadingMore(true);
      // Calculate offset for older messages
      const currentOffset = pagination.offset;
      const nextOffset = Math.max(0, currentOffset - 30);

      const result = await getMessages(id, 30, nextOffset);

      if (!result.success) {
        console.error("Error loading more messages:", result.error);
        return;
      }

      // Validate response with Zod
      const validatedResponse = paginatedMessagesResponseSchema.parse(
        result.data
      );

      if (validatedResponse.messages.length > 0) {
        // Transform and prepend older messages
        const olderMessages: ChatMessage[] = validatedResponse.messages.map(
          (msg: BackendMessage) => {
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

            // Add todos as reasoning part with variant "todos" (if present in metadata)
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
          }
        );

        // Save scroll position before adding messages
        const container = messagesContainerRef.current;
        const previousScrollHeight = container?.scrollHeight || 0;

        // Prepend older messages
        setMessages((prev) => [...olderMessages, ...prev]);

        // Restore scroll position after messages are added
        requestAnimationFrame(() => {
          if (container) {
            const newScrollHeight = container.scrollHeight;
            const scrollDifference = newScrollHeight - previousScrollHeight;
            container.scrollTop = scrollDifference;
          }
        });

        setPagination({
          total: validatedResponse.total,
          hasMore: validatedResponse.has_more,
          offset: validatedResponse.offset,
        });
      } else {
        setPagination((prev) => ({ ...prev, hasMore: false }));
      }
    } catch (error) {
      console.error("Error loading more messages:", error);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, pagination.hasMore, pagination.offset, id, setMessages]);

  return (
    <div className="overscroll-behavior-contain flex h-dvh min-w-0 touch-pan-y flex-col bg-background">
      <Messages
        chatId={id}
        isReadonly={false}
        messages={messages}
        regenerate={regenerate}
        selectedModelId={agentId || "hello-world"}
        setMessages={setMessages}
        status={status}
        votes={votes}
        onLoadMore={
          pagination.hasMore && !loadingMore ? loadMoreMessages : undefined
        }
        loadingMore={loadingMore}
        containerRef={messagesContainerRef}
      />

      <div className="sticky bottom-0 z-1 mx-auto flex w-full max-w-4xl flex-col gap-0 border-t-0 bg-background">
        <div className="flex gap-2 px-2 pb-3 md:px-4 md:pb-4">
          <MultimodalInput
            attachments={attachments}
            chatId={id}
            input={input}
            messages={messages}
            sendMessage={sendMessageWithTitleUpdate}
            setAttachments={setAttachments}
            setInput={setInput}
            setMessages={setMessages}
            status={status}
            stop={stop}
            usage={usage}
            agentName={agentName}
          />
        </div>
      </div>
    </div>
  );
}
