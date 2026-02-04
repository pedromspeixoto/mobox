"use client";

import { DataStreamProvider } from "@/components/data-stream-provider";
import { ChatSessionsProvider } from "@/contexts/chat-sessions-context";
import { SidebarProvider } from "@/components/ui/sidebar";

export function ChatProviders({
  children,
  defaultOpen,
}: {
  children: React.ReactNode;
  defaultOpen: boolean;
}) {
  return (
    <ChatSessionsProvider>
      <DataStreamProvider>
        <SidebarProvider defaultOpen={defaultOpen}>
          {children}
        </SidebarProvider>
      </DataStreamProvider>
    </ChatSessionsProvider>
  );
}
