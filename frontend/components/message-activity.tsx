"use client";

import { useEffect, useRef, useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ActivityIcon, ChevronDownIcon, Loader2Icon, BrainIcon, CheckCircle2Icon } from "lucide-react";
import { cn } from "@/lib/utils/generic";
import { Response } from "@/components/elements/response";
import type { TodoItem } from "@/components/message-todos";

type ActivityEntry = {
  variant: "processing" | "thinking";
  text: string;
};

type MessageActivityProps = {
  todos: TodoItem[];
  activityStream: ActivityEntry[];
  isLoading: boolean;
  messageId: string;
};

function TodoStatusBadge({ status }: { status?: TodoItem["status"] }) {
  if (status === "completed") {
    return (
      <span className="shrink-0 inline-flex items-center gap-0.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
        Done
      </span>
    );
  }
  if (status === "in_progress") {
    return (
      <span className="shrink-0 inline-flex items-center gap-0.5 rounded-full border border-blue-500/40 bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-medium text-blue-600 dark:text-blue-400">
        In progress
      </span>
    );
  }
  return (
    <span className="shrink-0 inline-flex items-center gap-0.5 rounded-full border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400">
      Todo
    </span>
  );
}

function TodoStrip({ items, isLoading }: { items: TodoItem[]; isLoading: boolean }) {
  const displayItems = isLoading
    ? items
    : items.map((i) =>
        i.status === "in_progress" ? { ...i, status: "completed" as const } : i
      );

  return (
    <ul
      className="flex flex-col gap-1 border-b border-border pb-2 mb-2 overflow-y-auto scrollbar-hide"
      style={{ maxHeight: `min(80vh, ${Math.max(4, displayItems.length) * 2.25}rem)` }}
    >
      {displayItems.map((item, index) => (
        <li
          key={index}
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1 text-[11px]",
            item.status === "completed"
              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400/90 border border-emerald-500/20"
              : item.status === "in_progress"
                ? "bg-blue-500/10 text-blue-600 dark:text-blue-400/90 border border-blue-500/30"
                : "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30"
          )}
        >
          {item.status === "completed" ? (
            <CheckCircle2Icon className="size-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
          ) : item.status === "in_progress" ? (
            <span className="size-2 rounded-full bg-blue-500 dark:bg-blue-400 shrink-0 animate-pulse" />
          ) : (
            <span className="size-2 rounded-full bg-amber-500 dark:bg-amber-400 shrink-0" />
          )}
          <span
            className={cn(
              "flex-1 min-w-0 break-words leading-tight",
              item.status === "completed" && "line-through opacity-80"
            )}
          >
            {item.content}
          </span>
          <TodoStatusBadge status={item.status} />
        </li>
      ))}
    </ul>
  );
}

function ActivityStream({ entries, isLoading }: { entries: ActivityEntry[]; isLoading: boolean }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevLengthRef = useRef(0);

  // Only scroll when a new step is added, not on every text update (reduces blinking)
  useEffect(() => {
    if (!isLoading || !scrollRef.current || entries.length <= prevLengthRef.current) {
      prevLengthRef.current = entries.length;
      return;
    }
    prevLengthRef.current = entries.length;
    const el = scrollRef.current;
    const raf = requestAnimationFrame(() => {
      el.scrollTop = el.scrollHeight;
    });
    return () => cancelAnimationFrame(raf);
  }, [entries.length, isLoading]);

  if (entries.length === 0) return null;

  return (
    <div
      ref={scrollRef}
      className="flex flex-col gap-2 max-h-64 overflow-y-auto scrollbar-hide"
    >
      {entries.map((entry, index) => (
        <div
          key={`${index}-${entry.variant}`}
          className="flex items-start gap-2 text-muted-foreground"
        >
          {entry.variant === "processing" ? (
            isLoading && index === entries.length - 1 ? (
              <Loader2Icon className="size-3.5 shrink-0 mt-0.5 animate-spin text-emerald-600 dark:text-emerald-500/80" />
            ) : null
          ) : (
            <BrainIcon className="size-3.5 shrink-0 mt-0.5 text-purple-600/80 dark:text-purple-400/70" />
          )}
          <div
            className={cn(
              "flex-1 min-w-0 text-[11px] leading-relaxed",
              entry.variant === "thinking" &&
                "border-l-2 border-purple-500/30 pl-2.5 py-0.5 prose prose-sm max-w-none dark:prose-invert [&_p]:my-0.5 [&_ul]:my-1 [&_ol]:my-1",
              entry.variant === "processing" && "pl-0"
            )}
          >
            {entry.variant === "processing" ? (
              <span className="whitespace-pre-wrap break-words">{entry.text.trim()}</span>
            ) : (
              <Response className="whitespace-pre-wrap break-words">{entry.text.trim()}</Response>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

const AUTO_CLOSE_DELAY = 500;

export function MessageActivity({
  todos,
  activityStream,
  isLoading,
  messageId,
}: MessageActivityProps) {
  const [isOpen, setIsOpen] = useState(isLoading);
  const [hasAutoClosed, setHasAutoClosed] = useState(false);
  const [hasBeenLoading, setHasBeenLoading] = useState(false);

  useEffect(() => {
    if (isLoading) {
      setIsOpen(true);
      setHasBeenLoading(true);
    }
  }, [isLoading]);

  // Auto-close only when streaming *just* ended (not when user opens an old message)
  useEffect(() => {
    if (hasBeenLoading && !isLoading && isOpen && !hasAutoClosed) {
      const timer = setTimeout(() => {
        setIsOpen(false);
        setHasAutoClosed(true);
      }, AUTO_CLOSE_DELAY);
      return () => clearTimeout(timer);
    }
  }, [hasBeenLoading, isLoading, isOpen, hasAutoClosed]);

  const taskCount = todos.length;
  const stepCount = activityStream.length;
  const summary = [
    taskCount > 0 && `${taskCount} task${taskCount !== 1 ? "s" : ""}`,
    stepCount > 0 && `${stepCount} step${stepCount !== 1 ? "s" : ""}`,
  ]
    .filter(Boolean)
    .join(" · ") || "Activity";

  return (
    <div
      className="w-full rounded-xl border border-border bg-muted/50 dark:border-zinc-700/60 dark:bg-zinc-900/50 px-4 py-3"
      data-testid="message-activity"
    >
      <Collapsible
        open={isOpen}
        onOpenChange={setIsOpen}
      >
        <CollapsibleTrigger
          className={cn(
            "flex w-full items-center justify-between gap-2 text-left text-muted-foreground text-xs transition-colors hover:text-foreground"
          )}
        >
          <div className="flex items-center gap-1.5">
            <ActivityIcon className="size-4 text-muted-foreground" />
            <span>{summary}</span>
            {isLoading && (
              <Loader2Icon className="size-3.5 animate-spin text-muted-foreground" />
            )}
          </div>
          <ChevronDownIcon
            className={cn(
              "size-3 shrink-0 text-muted-foreground transition-transform",
              isOpen ? "rotate-180" : "rotate-0"
            )}
          />
        </CollapsibleTrigger>
        <CollapsibleContent
          className={cn(
            "mt-3",
            "data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-top-2",
            "data-[state=open]:slide-in-from-top-2 outline-hidden",
            "data-[state=closed]:animate-out data-[state=open]:animate-in"
          )}
        >
          {todos.length > 0 && <TodoStrip items={todos} isLoading={isLoading} />}
          <ActivityStream entries={activityStream} isLoading={isLoading} />
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
