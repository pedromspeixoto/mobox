"use client";

import { useEffect, useState } from "react";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/elements/reasoning";
import { ProcessingTrigger } from "@/components/elements/processing-trigger";
import { cn } from "@/lib/utils/generic";

type MessageReasoningProps = {
  isLoading: boolean;
  reasoning: string;
  hasNewerBlock?: boolean;
  variant?: "processing" | "thinking";
};

export function MessageReasoning({
  isLoading,
  reasoning,
  hasNewerBlock = false,
  variant,
}: MessageReasoningProps) {
  const [hasBeenStreaming, setHasBeenStreaming] = useState(isLoading);
  const [isOpen, setIsOpen] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    if (isLoading) {
      setHasBeenStreaming(true);
    }
  }, [isLoading]);

  // Collapse when a newer block appears
  useEffect(() => {
    if (hasNewerBlock) {
      setIsOpen(false);
    }
  }, [hasNewerBlock]);

  // Use variant from providerMetadata - defaults to "thinking" if not specified
  const isProcessing = variant === "processing";

  // For processing content loaded from history (not streaming), start collapsed
  // For actively streaming content, start open
  const shouldStartOpen = isProcessing ? isLoading : hasBeenStreaming;

  // Block is only actively streaming if loading AND no newer block exists
  const isActivelyStreaming = isLoading && !hasNewerBlock;

  return (
    <div
      className={cn(
        "rounded-xl border px-4 py-3",
        isProcessing 
          ? "border-zinc-700 bg-zinc-800/80" 
          : "border-purple-500/40 bg-purple-900/40"
      )}
    >
      <Reasoning
        data-testid="message-reasoning"
        defaultOpen={shouldStartOpen}
        isStreaming={isActivelyStreaming}
        open={isOpen}
        onOpenChange={setIsOpen}
      >
        {isProcessing ? (
          <ProcessingTrigger />
        ) : (
          <ReasoningTrigger />
        )}
        <ReasoningContent>{reasoning}</ReasoningContent>
      </Reasoning>
    </div>
  );
}
