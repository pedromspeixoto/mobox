"use client";

import { memo } from "react";
import type { ComponentProps } from "react";
import { Loader2Icon, CheckCircle2Icon, ChevronDownIcon } from "lucide-react";
import { CollapsibleTrigger } from "@/components/ui/collapsible";
import { cn } from "@/lib/utils/generic";
import { useReasoning } from "@/components/elements/reasoning";

export type ProcessingTriggerProps = ComponentProps<typeof CollapsibleTrigger>;

export const ProcessingTrigger = memo(
  ({ className, children, ...props }: ProcessingTriggerProps) => {
    const { isStreaming, isOpen, duration } = useReasoning();

    // Determine the display state:
    // - isStreaming = true: Currently processing (show spinner)
    // - isStreaming = false && duration > 0: Just finished (show "Processed in Xs")
    // - isStreaming = false && duration === 0: Loaded from history (show "Processed")
    const isActive = isStreaming;

    return (
      <CollapsibleTrigger
        className={cn(
          "flex items-center gap-1.5 text-muted-foreground text-xs transition-colors hover:text-foreground",
          className
        )}
        {...props}
      >
        {children ?? (
          <>
            {isActive ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : (
              <CheckCircle2Icon className="size-4" />
            )}
            {isActive ? (
              <p>Processing...</p>
            ) : duration > 0 ? (
              <p>Processed in {duration}s</p>
            ) : (
              <p>Processed</p>
            )}
            <ChevronDownIcon
              className={cn(
                "size-3 text-muted-foreground transition-transform",
                isOpen ? "rotate-180" : "rotate-0"
              )}
            />
          </>
        )}
      </CollapsibleTrigger>
    );
  }
);

ProcessingTrigger.displayName = "ProcessingTrigger";
