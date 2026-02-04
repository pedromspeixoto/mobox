"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { getSessions } from "@/app/(chat)/actions/sessions";
import type { ChatSession } from "@/app/(chat)/actions/types";

interface ChatSessionsContextType {
  sessions: ChatSession[];
  loading: boolean;
  refreshSessions: () => void;
  updateSession: (sessionId: string, updates: Partial<ChatSession>) => void;
}

const ChatSessionsContext = createContext<ChatSessionsContextType | undefined>(
  undefined
);

export function ChatSessionsProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggerRefresh, setTriggerRefresh] = useState(0);

  const fetchSessions = useCallback(async () => {
    try {
      setLoading(true);
      const result = await getSessions();
      if (result.success) {
        setSessions(result.data);
      } else {
        console.error("Error fetching sessions:", result.error);
        setSessions([]);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [triggerRefresh, fetchSessions]);

  const refreshSessions = useCallback(() => {
    setTriggerRefresh((prev) => prev + 1);
  }, []);

  const updateSession = useCallback(
    (sessionId: string, updates: Partial<ChatSession>) => {
      setSessions((prev) => {
        const existing = prev.find((s) => s.id === sessionId);
        if (existing) {
          return prev.map((s) =>
            s.id === sessionId ? { ...s, ...updates } : s
          );
        }
        // Session not in list yet (e.g. fetch still in progress after page reload)
        // Add minimal session so sidebar updates immediately
        const now = new Date().toISOString();
        return [
          {
            id: sessionId,
            title: updates.title ?? null,
            agent_id: updates.agent_id ?? "hello-world",
            agent_name: updates.agent_name ?? null,
            created_at: updates.created_at ?? now,
            updated_at: updates.updated_at ?? now,
            sdk_session_id: updates.sdk_session_id ?? null,
          } as ChatSession,
          ...prev,
        ];
      });
    },
    []
  );

  return (
    <ChatSessionsContext.Provider
      value={{
        sessions,
        loading,
        refreshSessions,
        updateSession,
      }}
    >
      {children}
    </ChatSessionsContext.Provider>
  );
}

export function useChatSessions() {
  const context = useContext(ChatSessionsContext);
  if (context === undefined) {
    throw new Error("useChatSessions must be used within a ChatSessionsProvider");
  }
  return context;
}
