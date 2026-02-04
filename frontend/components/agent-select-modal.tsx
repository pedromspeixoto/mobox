"use client";

import { useEffect, useState } from "react";
import { getAgents, type Agent } from "@/app/(chat)/actions";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/spinner";
import { Bot, Sparkles, ChevronRight, AlertCircle } from "lucide-react";

interface AgentSelectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectAgent: (agent: Agent) => void;
}

function formatFramework(framework: string): string {
  const labels: Record<string, string> = {
    claude: "Claude",
    deepagents: "DeepAgents",
    langchain: "LangChain",
  };
  return labels[framework?.toLowerCase()] ?? framework;
}

function getFrameworkBadgeClass(framework: string): string {
  const f = framework?.toLowerCase();
  if (f === "claude") return "border-orange-200 bg-orange-100 text-orange-800 dark:border-orange-800 dark:bg-orange-950/50 dark:text-orange-200";
  if (f === "deepagents" || f === "langchain") return "border-violet-200 bg-violet-100 text-violet-800 dark:border-violet-800 dark:bg-violet-950/50 dark:text-violet-200";
  return "border-border bg-muted text-muted-foreground";
}

export function AgentSelectModal({
  open,
  onOpenChange,
  onSelectAgent,
}: AgentSelectModalProps) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      fetchAgents();
    }
  }, [open]);

  const fetchAgents = async () => {
    setLoading(true);
    setError(null);

    const result = await getAgents();

    if (result.success) {
      setAgents(result.data);
    } else {
      setError(result.error);
    }

    setLoading(false);
  };

  const handleSelect = (agent: Agent) => {
    onSelectAgent(agent);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            Select an Agent
          </DialogTitle>
          <DialogDescription className="text-sm">
            Choose an agent to start your conversation with.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12">
              <LoadingSpinner size="lg" />
              <p className="mt-4 text-sm text-muted-foreground">Loading agents...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="rounded-full bg-destructive/10 p-3">
                <AlertCircle className="h-6 w-6 text-destructive" />
              </div>
              <p className="mt-4 text-sm font-medium text-destructive">{error}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={fetchAgents}
              >
                Try Again
              </Button>
            </div>
          ) : agents.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center">
              <div className="rounded-full bg-muted p-3">
                <Bot className="h-6 w-6 text-muted-foreground" />
              </div>
              <p className="mt-4 text-sm text-muted-foreground">
                No agents available at the moment
              </p>
            </div>
          ) : (
            <ul
              role="listbox"
              aria-label="Available agents"
              className="h-[320px] overflow-y-auto rounded-lg border border-border divide-y divide-border"
            >
              {agents.map((agent) => (
                <li key={agent.id} role="option">
                  <button
                    type="button"
                    onClick={() => handleSelect(agent)}
                    className="group flex w-full items-center gap-2.5 px-3 py-2.5 text-left transition-colors hover:bg-muted/50 focus:bg-muted/50 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-inset"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-foreground truncate">
                          {agent.name}
                        </span>
                        <Badge
                          variant="outline"
                          className={`shrink-0 text-[9px] font-medium uppercase tracking-wide ${getFrameworkBadgeClass(agent.framework ?? "claude")}`}
                        >
                          {formatFramework(agent.framework ?? "claude")}
                        </Badge>
                      </div>
                      <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-2">
                        {agent.description}
                      </p>
                    </div>
                    <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
