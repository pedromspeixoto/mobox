"use client";

import { useState } from "react";
import { MessageSquarePlus, Sparkles, Shield, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AgentSelectModal } from "@/components/agent-select-modal";
import { MoboxLogo } from "@/components/mobox-logo";
import { useChatSessions } from "@/contexts/chat-sessions-context";
import { createSession, type Agent } from "@/app/(chat)/actions";
import { toast } from "@/components/toast";

export default function LandingPage() {
  const { refreshSessions } = useChatSessions();
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  const handleSelectAgent = async (agent: Agent) => {
    if (isCreating) return;

    setIsCreating(true);

    try {
      const result = await createSession(agent.id, agent.name);

      if (result.success) {
        console.log("Session created successfully:", result.data.id);

        // Close modal immediately for better UX
        setShowAgentModal(false);

        // Refresh sessions list
        refreshSessions();

        // Use window.location for a full page reload to ensure fresh data
        window.location.href = `/chat/${result.data.id}`;
      } else {
        console.error("Failed to create session:", result.error);
        toast({
          type: "error",
          description: result.error || "Failed to create chat session",
        });
        setIsCreating(false);
      }
    } catch (error) {
      console.error("Error creating session:", error);
      toast({
        type: "error",
        description: "An unexpected error occurred",
      });
      setIsCreating(false);
    }
  };

  return (
    <>
      <div className="relative flex h-dvh flex-col items-center justify-center overflow-hidden bg-background px-4">
        {/* Background gradient effects */}
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute -left-40 -top-40 h-80 w-80 rounded-full bg-primary/5 blur-3xl" />
          <div className="absolute -right-40 -bottom-40 h-80 w-80 rounded-full bg-primary/5 blur-3xl" />
          <div className="absolute left-1/2 top-1/2 h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/3 blur-3xl" />
        </div>

        <div className="flex max-w-4xl flex-col items-center text-center">
          {/* Logo with animation */}
          <div className="mb-6 animate-fade-in-up">
            <div className="relative">
              <div className="absolute inset-0 animate-pulse rounded-2xl bg-primary/20 blur-xl" />
              <div className="relative flex items-center justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 p-4 shadow-lg backdrop-blur-sm">
                <MoboxLogo size={48} className="text-primary" />
              </div>
            </div>
          </div>

          {/* Title with gradient */}
          <h1 className="mb-4 animate-fade-in-up text-3xl font-bold tracking-tight sm:text-4xl md:text-5xl" style={{ animationDelay: "0.1s" }}>
            Welcome to{" "}
            <span className="bg-gradient-to-r from-primary via-primary/80 to-primary/60 bg-clip-text text-transparent">
              MOBOX
            </span>
          </h1>

          {/* Subtitle */}
          <p className="mb-10 max-w-2xl animate-fade-in-up text-base text-muted-foreground sm:text-lg" style={{ animationDelay: "0.2s" }}>
            Run AI agents in isolated sandboxes. Experience secure, powerful conversations with specialized agents.
          </p>

          {/* Features Grid */}
          <div className="mb-8 grid w-full max-w-3xl gap-3 animate-fade-in-up sm:grid-cols-3" style={{ animationDelay: "0.3s" }}>
            <div className="group relative overflow-hidden rounded-xl border border-border bg-card p-4 text-left transition-all hover:border-primary hover:shadow-lg hover:shadow-primary/5">
              <div className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="mb-2 inline-flex rounded-lg bg-primary/10 p-2">
                <Sparkles className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mb-1 text-sm font-semibold text-foreground">Multiple Agents</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Choose from different AI agents specialized for various tasks
              </p>
            </div>

            <div className="group relative overflow-hidden rounded-xl border border-border bg-card p-4 text-left transition-all hover:border-primary hover:shadow-lg hover:shadow-primary/5">
              <div className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="mb-2 inline-flex rounded-lg bg-primary/10 p-2">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mb-1 text-sm font-semibold text-foreground">Isolated Sandboxes</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Secure execution environment for safe AI interactions
              </p>
            </div>

            <div className="group relative overflow-hidden rounded-xl border border-border bg-card p-4 text-left transition-all hover:border-primary hover:shadow-lg hover:shadow-primary/5">
              <div className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
              <div className="mb-2 inline-flex rounded-lg bg-primary/10 p-2">
                <Zap className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mb-1 text-sm font-semibold text-foreground">Persistent Sessions</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Your conversations are saved and can be continued anytime
              </p>
            </div>
          </div>

          {/* CTA Button */}
          <div className="animate-fade-in-up" style={{ animationDelay: "0.4s" }}>
            <Button
              size="default"
              onClick={() => setShowAgentModal(true)}
              disabled={isCreating}
              className="group relative gap-2 shadow-lg transition-all hover:shadow-xl hover:shadow-primary/20"
            >
              <MessageSquarePlus className="h-4 w-4 transition-transform group-hover:scale-110" />
              {isCreating ? "Creating..." : "Start New Chat"}
            </Button>
          </div>
        </div>
      </div>

      <AgentSelectModal
        open={showAgentModal}
        onOpenChange={setShowAgentModal}
        onSelectAgent={handleSelectAgent}
      />
    </>
  );
}
