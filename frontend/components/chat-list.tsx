"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, MoreHorizontal, Trash2 } from "lucide-react";
import { useChatSessions } from "@/contexts/chat-sessions-context";
import { deleteSession } from "@/app/(chat)/actions/sessions";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/spinner";
import { toast } from "@/components/toast";
import { cn } from "@/lib/utils/generic";

export function ChatList() {
  const pathname = usePathname();
  const { sessions, loading, refreshSessions } = useChatSessions();

  const handleDeleteSession = async (
    chatId: string,
    event: React.MouseEvent
  ) => {
    event.preventDefault();
    event.stopPropagation();

    const result = await deleteSession(chatId);

    if (result.success) {
      toast({
        type: "success",
        description: "Chat session deleted",
      });

      // If we deleted the current chat, redirect to home with full page reload
      if (pathname?.includes(chatId)) {
        window.location.href = "/";
      } else {
        // Otherwise just refresh the list
        refreshSessions();
      }
    } else {
      console.error("Error deleting session:", result.error);
      toast({
        type: "error",
        description: "Failed to delete session",
      });
    }
  };

  if (loading) {
    return (
      <SidebarGroup>
        <SidebarGroupContent>
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="md" />
          </div>
        </SidebarGroupContent>
      </SidebarGroup>
    );
  }

  if (sessions.length === 0) {
    return (
      <SidebarGroup>
        <SidebarGroupContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <MessageSquare className="h-8 w-8 text-muted-foreground/50 mb-2" />
            <p className="text-sm text-muted-foreground">No chats yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Start a new conversation
            </p>
          </div>
        </SidebarGroupContent>
      </SidebarGroup>
    );
  }

  return (
    <SidebarGroup>
      <SidebarGroupContent>
        <SidebarMenu className="gap-1 px-2">
          {sessions.map((session) => {
            const isActive = pathname?.includes(session.id);
            const displayTitle = session.title || "New Chat";
            const agentName = session.agent_name;

            return (
              <SidebarMenuItem key={session.id} className="group/item relative">
                <Link
                  href={`/chat/${session.id}`}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-2.5 py-2 transition-all duration-200 w-full",
                    "hover:bg-accent/50",
                    isActive && "bg-accent"
                  )}
                >
                  {/* Icon */}
                  <MessageSquare className={cn(
                    "h-4 w-4 shrink-0 transition-colors",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )} />

                  {/* Content */}
                  <div className="flex-1 min-w-0 pr-8">
                    <div className="flex flex-col gap-0.5">
                      <span className={cn(
                        "truncate text-sm font-medium leading-tight",
                        isActive ? "text-foreground" : "text-foreground/90"
                      )}>
                        {displayTitle}
                      </span>
                      {agentName && (
                        <span className="truncate text-xs text-muted-foreground">
                          {agentName}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Delete button - shows on hover */}
                  <div className="absolute right-2 top-1/2 -translate-y-1/2">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className={cn(
                            "h-7 w-7 p-0 opacity-0 group-hover/item:opacity-100 transition-opacity",
                            "hover:bg-accent hover:text-foreground"
                          )}
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                          }}
                        >
                          <span className="sr-only">More options</span>
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-40">
                        <DropdownMenuItem
                          onClick={(e) => handleDeleteSession(session.id, e)}
                          className="text-destructive focus:text-destructive focus:bg-destructive/10 cursor-pointer"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </Link>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
