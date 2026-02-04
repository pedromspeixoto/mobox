"use client";
import equal from "fast-deep-equal";
import { motion } from "framer-motion";
import { memo } from "react";
import type { ChatMessage } from "@/lib/types";
import { sanitizeText } from "@/lib/utils/messages";
import { cn } from "@/lib/utils/generic";
import { MessageContent } from "@/components/elements/message";
import { Response } from "@/components/elements/response";
import { SparklesIcon } from "@/components/icons";
import { MessageActions } from "@/components/message-actions";
import { MessageActivity } from "@/components/message-activity";
import type { TodoItem } from "@/components/message-todos";
import { PreviewAttachment } from "@/components/preview-attachment";

const PurePreviewMessage = ({
  message,
  isLoading,
  isReadonly,
  requiresScrollPadding,
}: {
  message: ChatMessage;
  isLoading: boolean;
  isReadonly: boolean;
  requiresScrollPadding: boolean;
}) => {

  const attachmentsFromMessage = message.parts.filter(
    (part) => part.type === "file"
  );

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="group/message w-full"
      data-role={message.role}
      data-testid={`message-${message.role}`}
      initial={{ opacity: 0 }}
    >
      <div
        className={cn("flex w-full items-start gap-2 md:gap-3", {
          "justify-end": message.role === "user",
          "justify-start": message.role === "assistant",
        })}
      >
        {message.role === "assistant" && (
          <div className={cn(
            "-mt-1 flex size-8 shrink-0 items-center justify-center rounded-full bg-background ring-1 ring-border",
            isLoading && "animate-glow-ring"
          )}>
            <span className={cn(isLoading && "animate-ai-thinking text-purple-400")}>
              <SparklesIcon size={14} />
            </span>
          </div>
        )}

        <div
          className={cn("flex flex-col", {
            "gap-2 md:gap-4": message.parts?.some(
              (p) => p.type === "text" && p.text?.trim()
            ),
            "min-h-96": message.role === "assistant" && requiresScrollPadding,
            "w-full":
              message.role === "assistant" &&
              (message.parts?.some(
                (p) => p.type === "text" && p.text?.trim()
              ) ||
                message.parts?.some(
                  (p) =>
                    p.type === "reasoning" &&
                    ("text" in p
                      ? (p as { text?: string }).text?.trim() ||
                        (p.providerMetadata?.mobox as { variant?: string })?.variant === "todos"
                      : false)
                )),
            "max-w-[calc(100%-2.5rem)] sm:max-w-[min(fit-content,80%)]":
              message.role === "user",
          })}
        >
          {attachmentsFromMessage.length > 0 && (
            <div
              className="flex flex-row justify-end gap-2"
              data-testid={"message-attachments"}
            >
              {attachmentsFromMessage.map((attachment) => (
                <PreviewAttachment
                  attachment={{
                    name: attachment.filename ?? "file",
                    contentType: attachment.mediaType,
                    url: attachment.url,
                  }}
                  key={attachment.url}
                />
              ))}
            </div>
          )}

          {/* Unified Activity panel: todo strip at top + chronological activity stream */}
          {(() => {
            type ReasoningPart = { type: "reasoning"; text: string; providerMetadata?: { mobox?: { variant?: string } } };
            const reasoningParts = (message.parts ?? []).filter(
              (p): p is ReasoningPart => p.type === "reasoning" && "text" in p
            );
            const hasAnyReasoning = reasoningParts.some(
              (p) =>
                p.text?.trim().length > 0 ||
                (p.providerMetadata?.mobox as { variant?: string })?.variant === "todos"
            );
            if (!hasAnyReasoning) return null;

            // Latest todos (from last todos part)
            const todosParts = reasoningParts.filter(
              (p) => (p.providerMetadata?.mobox as { variant?: string })?.variant === "todos"
            );
            let todosItems: TodoItem[] = [];
            if (todosParts.length > 0) {
              try {
                const parsed = JSON.parse(todosParts[todosParts.length - 1].text || "[]") as TodoItem[];
                if (Array.isArray(parsed) && parsed.length > 0) todosItems = parsed;
              } catch {
                // Invalid JSON
              }
            }

            // Activity stream: processing as separate entries, thinking as one merged block
            const processingEntries: string[] = [];
            const thinkingParts: string[] = [];
            for (const p of reasoningParts) {
              const v = (p.providerMetadata?.mobox as { variant?: string })?.variant;
              if (v !== "processing" && v !== "thinking" || !p.text?.trim()) continue;
              const text = p.text.trim();
              if (v === "processing") {
                processingEntries.push(...text.split(/\n+/).filter(Boolean));
              } else {
                thinkingParts.push(text);
              }
            }
            const activityStream: { variant: "processing" | "thinking"; text: string }[] = [
              ...processingEntries.map((t) => ({ variant: "processing" as const, text: t })),
              ...(thinkingParts.length > 0
                ? [{ variant: "thinking" as const, text: thinkingParts.join("\n\n") }]
                : []),
            ];

            return (
              <MessageActivity
                key={`${message.id}-activity`}
                activityStream={activityStream}
                isLoading={isLoading}
                messageId={message.id}
                todos={todosItems}
              />
            );
          })()}

          {/* Text parts */}
          {message.parts?.map((part, index) => {
            const { type } = part;
            const key = `message-${message.id}-part-${index}`;

            // Skip reasoning parts - they're rendered above
            if (type === "reasoning") {
              return null;
            }

            if (type === "text") {
              return (
                <div key={key}>
                  <MessageContent
                    className={cn({
                      "w-fit break-words rounded-2xl px-3 py-2 text-right text-white":
                        message.role === "user",
                      "bg-transparent px-0 py-0 text-left text-xs":
                        message.role === "assistant",
                    })}
                    data-testid="message-content"
                    style={
                      message.role === "user"
                        ? { backgroundColor: "#006cff" }
                        : undefined
                    }
                  >
                    <Response>{sanitizeText(part.text)}</Response>
                  </MessageContent>
                </div>
              );
            }

            return null;
          })}

          {/* Message actions */}
          {!isReadonly && (
            <MessageActions
              isLoading={isLoading}
              key={`action-${message.id}`}
              message={message}
            />
          )}
        </div>
      </div>
    </motion.div>
  );
};

export const PreviewMessage = memo(
  PurePreviewMessage,
  (prevProps, nextProps) => {
    if (prevProps.isLoading !== nextProps.isLoading) {
      return false;
    }
    if (prevProps.message.id !== nextProps.message.id) {
      return false;
    }
    if (prevProps.requiresScrollPadding !== nextProps.requiresScrollPadding) {
      return false;
    }
    if (!equal(prevProps.message.parts, nextProps.message.parts)) {
      return false;
    }

    return false;
  }
);

export const ThinkingMessage = () => {
  const role = "assistant";

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="group/message w-full"
      data-role={role}
      data-testid="message-assistant-loading"
      exit={{ opacity: 0, transition: { duration: 0.5 } }}
      initial={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className="flex items-start justify-start gap-3">
        <div className="-mt-1 flex size-8 shrink-0 items-center justify-center rounded-full bg-background ring-1 ring-border animate-pulse">
          <SparklesIcon size={14} />
        </div>

        <div className="flex w-full flex-col gap-2 md:gap-4">
          <div className="p-0 text-muted-foreground text-sm">Thinking...</div>
        </div>
      </div>
    </motion.div>
  );
};
