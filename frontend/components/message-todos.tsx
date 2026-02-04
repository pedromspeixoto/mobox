"use client";

import { useEffect, useState } from "react";
import { Reasoning, ReasoningTrigger, useReasoning } from "@/components/elements/reasoning";
import { CollapsibleContent } from "@/components/ui/collapsible";
import { ListTodoIcon, ChevronDownIcon, CheckIcon, CircleIcon, Loader2Icon } from "lucide-react";
import { cn } from "@/lib/utils/generic";

function TodosTrigger({
  totalCount,
  completedCount,
  inProgressCount,
}: {
  totalCount: number;
  completedCount: number;
  inProgressCount: number;
}) {
  const { isOpen } = useReasoning();
  return (
    <ReasoningTrigger>
      <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
        <ListTodoIcon className="size-4 text-amber-400" />
        <span>
          {totalCount} task{totalCount !== 1 ? "s" : ""}
          {completedCount > 0 && (
            <span className="text-emerald-400/90">
              {" "}
              · {completedCount} done
            </span>
          )}
          {inProgressCount > 0 && (
            <span className="text-blue-400/90">
              {" "}
              · {inProgressCount} in progress
            </span>
          )}
        </span>
        <ChevronDownIcon
          className={cn(
            "size-3 text-muted-foreground transition-transform",
            isOpen ? "rotate-180" : "rotate-0"
          )}
        />
      </div>
    </ReasoningTrigger>
  );
}

export type TodoItem = {
  content: string;
  status?: "pending" | "in_progress" | "completed";
};

type MessageTodosProps = {
  items: TodoItem[];
  isLoading?: boolean;
  hasNewerBlock?: boolean;
};

function TodoStatusBadge({ status }: { status: TodoItem["status"] }) {
  if (!status || status === "pending") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-[10px] font-medium text-amber-400">
        <CircleIcon className="size-2.5" />
        Pending
      </span>
    );
  }
  if (status === "in_progress") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-blue-500/40 bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-medium text-blue-400">
        <Loader2Icon className="size-2.5 animate-spin" />
        In progress
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400">
      <CheckIcon className="size-2.5" />
      Done
    </span>
  );
}

export function MessageTodos({
  items,
  isLoading = false,
  hasNewerBlock = false,
}: MessageTodosProps) {
  const [isOpen, setIsOpen] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    if (hasNewerBlock) {
      setIsOpen(false);
    }
  }, [hasNewerBlock]);

  // When agent has stopped, treat any "in_progress" as "completed" since the response is done
  const displayItems = isLoading
    ? items
    : items.map((i) =>
        i.status === "in_progress" ? { ...i, status: "completed" as const } : i
      );

  const completedCount = displayItems.filter((i) => i.status === "completed").length;
  const inProgressCount = displayItems.filter((i) => i.status === "in_progress").length;
  const totalCount = displayItems.length;

  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 px-4 py-3">
      <Reasoning
        data-testid="message-todos"
        defaultOpen={isLoading}
        isStreaming={isLoading}
        open={isOpen}
        onOpenChange={setIsOpen}
      >
        <TodosTrigger
          totalCount={totalCount}
          completedCount={completedCount}
          inProgressCount={inProgressCount}
        />
        <CollapsibleContent
          className="mt-2 overflow-y-auto scrollbar-hide data-[state=closed]:fade-out-0 data-[state=closed]:slide-out-to-top-2 data-[state=open]:slide-in-from-top-2 outline-hidden data-[state=closed]:animate-out data-[state=open]:animate-in"
          style={{ maxHeight: `min(80vh, ${Math.max(4, displayItems.length) * 2.75}rem)` }}
        >
          <ul className="grid gap-2">
            {displayItems.map((item, index) => (
              <li
                key={`${index}-${item.content.slice(0, 20)}`}
                className={cn(
                  "flex items-start gap-2 rounded-lg border px-3 py-2",
                  item.status === "completed"
                    ? "border-emerald-500/20 bg-emerald-950/10"
                    : "border-zinc-700/50 bg-zinc-800/30"
                )}
              >
                <div className="mt-0.5 shrink-0">
                  {item.status === "completed" ? (
                    <CheckIcon className="size-4 text-emerald-400" />
                  ) : (
                    <CircleIcon className="size-4 text-muted-foreground/60" />
                  )}
                </div>
                <div className="min-w-0 flex-1 flex items-center gap-2">
                  <span
                    className={cn(
                      "text-xs text-foreground",
                      item.status === "completed" && "text-muted-foreground line-through"
                    )}
                  >
                    {item.content}
                  </span>
                  <TodoStatusBadge status={item.status} />
                </div>
              </li>
            ))}
          </ul>
        </CollapsibleContent>
      </Reasoning>
    </div>
  );
}
