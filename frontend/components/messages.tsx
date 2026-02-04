"use client";

import type { UseChatHelpers } from "@ai-sdk/react";
import equal from "fast-deep-equal";
import { AnimatePresence } from "framer-motion";
import { ArrowDownIcon } from "lucide-react";
import { memo, useEffect, useRef, useState } from "react";
type Vote = never;
import type { ChatMessage } from "@/lib/types";
import { Conversation, ConversationContent } from "@/components/elements/conversation";
import { Greeting } from "@/components/greeting";
import { PreviewMessage, ThinkingMessage } from "@/components/message";
import { LoadingSpinner } from "@/components/ui/spinner";

type MessagesProps = {
  chatId: string;
  status: UseChatHelpers<ChatMessage>["status"];
  votes: Vote[] | undefined;
  messages: ChatMessage[];
  setMessages: UseChatHelpers<ChatMessage>["setMessages"];
  regenerate: UseChatHelpers<ChatMessage>["regenerate"];
  isReadonly: boolean;
  selectedModelId: string;
  onLoadMore?: () => void;
  loadingMore?: boolean;
  containerRef?: React.RefObject<HTMLDivElement>;
};

function PureMessages({
  chatId,
  status,
  votes,
  messages,
  setMessages,
  regenerate,
  isReadonly,
  onLoadMore,
  loadingMore = false,
  containerRef: externalContainerRef,
}: MessagesProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const [hasSentMessage, setHasSentMessage] = useState(false);

  // Track when user has sent a message and stick to bottom
  useEffect(() => {
    if (status === "submitted") {
      setHasSentMessage(true);
      setIsAtBottom(true);
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [status]);

  // Check if user is at bottom
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const isBottom =
        Math.abs(container.scrollHeight - container.scrollTop - container.clientHeight) < 10;
      setIsAtBottom(isBottom);
    };

    container.addEventListener("scroll", handleScroll);
    return () => container.removeEventListener("scroll", handleScroll);
  }, []);

  // Get the last message's content length for scroll tracking
  const lastMessage = messages[messages.length - 1];
  const lastMessageContentLength = lastMessage?.parts?.reduce((acc, part) => {
    if (part.type === "text" && "text" in part) return acc + (part.text?.length || 0);
    return acc;
  }, 0) || 0;

  // Scroll to bottom when new content arrives, but only if user is already at bottom.
  // If user has scrolled up, respect that and do not force scroll.
  // Exception: when user just sent a message (submitted/streaming), stick to bottom.
  useEffect(() => {
    if (messages.length > 0 && messagesEndRef.current && isAtBottom) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages.length, lastMessageContentLength, isAtBottom, status]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div
      className="overscroll-behavior-contain -webkit-overflow-scrolling-touch flex-1 touch-pan-y overflow-y-scroll"
      ref={containerRef}
      style={{ overflowAnchor: "none" }}
    >
      <Conversation className="mx-auto flex min-w-0 max-w-4xl flex-col gap-4 md:gap-6">
        <ConversationContent className="flex flex-col gap-4 px-2 py-4 md:gap-6 md:px-4">
          {loadingMore && (
            <div className="flex justify-center py-4">
              <LoadingSpinner size="md" />
            </div>
          )}
          {messages.length === 0 && <Greeting />}

          {messages.map((message, index) => (
            <PreviewMessage
              isLoading={
                status === "streaming" && messages.length - 1 === index
              }
              isReadonly={isReadonly}
              key={message.id}
              message={message}
              requiresScrollPadding={
                hasSentMessage && index === messages.length - 1
              }
            />
          ))}

          <AnimatePresence mode="wait">
            {status === "submitted" && <ThinkingMessage key="thinking" />}
          </AnimatePresence>

          <div className="h-4 shrink-0" ref={messagesEndRef} />
        </ConversationContent>
      </Conversation>

      {!isAtBottom && (
        <button
          aria-label="Scroll to bottom"
          className="-translate-x-1/2 absolute bottom-40 left-1/2 z-10 rounded-full border bg-background p-2 shadow-lg transition-colors hover:bg-muted"
          onClick={scrollToBottom}
          type="button"
        >
          <ArrowDownIcon className="size-4" />
        </button>
      )}
    </div>
  );
}

export const Messages = memo(PureMessages, (prevProps, nextProps) => {
  if (prevProps.status !== nextProps.status) {
    return false;
  }
  if (prevProps.selectedModelId !== nextProps.selectedModelId) {
    return false;
  }
  if (prevProps.messages.length !== nextProps.messages.length) {
    return false;
  }
  if (!equal(prevProps.messages, nextProps.messages)) {
    return false;
  }
  if (!equal(prevProps.votes, nextProps.votes)) {
    return false;
  }

  return false;
});
