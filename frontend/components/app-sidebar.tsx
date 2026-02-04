"use client";

import { useState } from "react";
import Link from "next/link";
import { PlusIcon } from "@/components/icons";
import { SidebarUserNav } from "@/components/sidebar-user-nav";
import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ChatList } from "@/components/chat-list";
import { AgentSelectModal } from "@/components/agent-select-modal";
import { useChatSessions } from "@/contexts/chat-sessions-context";
import { createSession, deleteAllSessions, type Agent } from "@/app/(chat)/actions";
import { toast } from "@/components/toast";
import { Trash2Icon } from "lucide-react";

export function AppSidebar() {
  const { setOpenMobile } = useSidebar();
  const { refreshSessions } = useChatSessions();
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [deletingAll, setDeletingAll] = useState(false);
  const [showDeleteAllDialog, setShowDeleteAllDialog] = useState(false);

  const handleNewChatClick = () => {
    setShowAgentModal(true);
  };

  const handleSelectAgent = async (agent: Agent) => {
    if (isCreating) return;

    setIsCreating(true);
    setOpenMobile(false);

    try {
      // Create session in backend
      const result = await createSession(agent.id, agent.name);

      if (result.success) {
        console.log("Session created successfully:", result.data.id);

        // Refresh session list
        refreshSessions();

        // Close modal
        setShowAgentModal(false);

        // Use window.location for a full page reload to ensure fresh data
        window.location.href = `/chat/${result.data.id}`;
      } else {
        console.error("Failed to create session:", result.error);
        toast({
          type: "error",
          description: result.error || "Failed to create chat session",
        });
        setIsCreating(false);
        setShowAgentModal(false);
      }
    } catch (error) {
      console.error("Error creating session:", error);
      toast({
        type: "error",
        description: "An unexpected error occurred",
      });
      setIsCreating(false);
      setShowAgentModal(false);
    }
  };

  const handleDeleteAllClick = () => {
    setShowDeleteAllDialog(true);
  };

  const handleConfirmDeleteAll = async () => {
    setShowDeleteAllDialog(false);

    try {
      setDeletingAll(true);
      const result = await deleteAllSessions();

      if (result.success) {
        toast({
          type: "success",
          description: "All chat sessions deleted",
        });
        refreshSessions();
        // Use window.location for full page reload
        window.location.href = "/";
      } else {
        console.error("Error deleting all sessions:", result.error);
        toast({
          type: "error",
          description: "Failed to delete all sessions",
        });
        setDeletingAll(false);
      }
    } catch (error) {
      console.error("Error deleting all sessions:", error);
      toast({
        type: "error",
        description: "An unexpected error occurred",
      });
      setDeletingAll(false);
    }
  };

  return (
    <>
      <Sidebar className="group-data-[side=left]:border-r-0">
        <SidebarHeader className="border-b border-border/50">
          <SidebarMenu>
            <div className="flex flex-row items-center justify-between px-2 py-3">
              <Link
                href="/"
                onClick={() => {
                  setOpenMobile(false);
                }}
                className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-accent transition-colors"
              >
                <span className="font-bold text-lg tracking-tight">
                  MOBOX
                </span>
              </Link>
              <div className="flex items-center gap-0.5">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleNewChatClick}
                      disabled={isCreating}
                      className="h-8 w-8 p-0"
                    >
                      <PlusIcon size={16} />
                      <span className="sr-only">New Chat</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    New Chat
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleDeleteAllClick}
                      disabled={deletingAll}
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                    >
                      <Trash2Icon className="h-4 w-4" />
                      <span className="sr-only">Delete All</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    Delete All Sessions
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          </SidebarMenu>
        </SidebarHeader>
        <SidebarContent>
          <ChatList />
        </SidebarContent>
        <SidebarFooter>
          <SidebarUserNav />
        </SidebarFooter>
      </Sidebar>

      <AgentSelectModal
        open={showAgentModal}
        onOpenChange={setShowAgentModal}
        onSelectAgent={handleSelectAgent}
      />

      <AlertDialog open={showDeleteAllDialog} onOpenChange={setShowDeleteAllDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete All Sessions?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete all chat sessions? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDeleteAll}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deletingAll ? "Deleting..." : "Delete All"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
