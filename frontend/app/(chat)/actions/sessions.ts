"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";
import { backend, BackendError } from "@/lib/api/backend";
import {
  ChatSessionResponseSchema,
  PaginatedMessagesResponseSchema,
  ChatContextResponseSchema,
  DeleteSessionResponseSchema,
  DeleteAllSessionsResponseSchema,
  type ChatSessionResponse,
  type CreateSessionRequest,
  type PaginatedMessagesResponse,
  type ChatContextResponse,
  type DeleteSessionResponse,
  type DeleteAllSessionsResponse,
} from "@/lib/api/contracts";
import type { ActionResult } from "./types";

// ============================================================================
// Server Actions
// ============================================================================

/**
 * Get all chat sessions, ordered by most recently updated
 * Backend: GET /api/v1/sessions/
 */
export async function getSessions(): Promise<ActionResult<ChatSessionResponse[]>> {
  try {
    const data = await backend.get<ChatSessionResponse[]>("/sessions/");
    const validatedData = z.array(ChatSessionResponseSchema).parse(data);
    return { success: true, data: validatedData };
  } catch (error) {
    console.error("[getSessions] Error:", error);

    if (error instanceof BackendError) {
      return {
        success: false,
        error: error.message,
        code: error.statusCode,
      };
    }

    if (error instanceof z.ZodError) {
      console.error("[getSessions] Validation error:", error.errors);
      return { success: false, error: "Invalid response from server" };
    }

    return { success: false, error: "Failed to fetch sessions" };
  }
}

/**
 * Create a new chat session with the specified agent
 * Backend: POST /api/v1/sessions/
 */
export async function createSession(
  agentId: string,
  agentName: string,
  title?: string
): Promise<ActionResult<ChatSessionResponse>> {
  try {
    const requestBody: CreateSessionRequest = {
      agent_id: agentId,
      agent_name: agentName,
      title,
    };
    const data = await backend.post<ChatSessionResponse>("/sessions/", requestBody);
    const validatedData = ChatSessionResponseSchema.parse(data);

    // Revalidate paths that depend on sessions data
    revalidatePath("/");
    revalidatePath(`/chat/${validatedData.id}`);

    return { success: true, data: validatedData };
  } catch (error) {
    console.error("[createSession] Error:", error);

    if (error instanceof BackendError) {
      return {
        success: false,
        error: error.message,
        code: error.statusCode,
      };
    }

    if (error instanceof z.ZodError) {
      console.error("[createSession] Validation error:", error.errors);
      return { success: false, error: "Invalid response from server" };
    }

    return { success: false, error: "Failed to create session" };
  }
}

/**
 * Get paginated messages for a chat session
 * Backend: GET /api/v1/sessions/{chat_id}/messages
 */
export async function getMessages(
  chatId: string,
  limit = 30,
  offset = 0
): Promise<ActionResult<PaginatedMessagesResponse>> {
  try {
    const url = `/sessions/${chatId}/messages?limit=${limit}&offset=${offset}`;
    const data = await backend.get<PaginatedMessagesResponse>(url);
    const validatedData = PaginatedMessagesResponseSchema.parse(data);
    return { success: true, data: validatedData };
  } catch (error) {
    console.error(`[getMessages] Error for chat ${chatId}:`, error);

    if (error instanceof BackendError) {
      // For 404 (session not found), return error
      if (error.isNotFound()) {
        return {
          success: false,
          error: "Chat session not found",
          code: 404,
        };
      }

      return {
        success: false,
        error: error.message,
        code: error.statusCode,
      };
    }

    if (error instanceof z.ZodError) {
      console.error("[getMessages] Validation error:", error.errors);
      return { success: false, error: "Invalid response from server" };
    }

    return { success: false, error: "Failed to fetch messages" };
  }
}

/**
 * Get usage context/statistics for a chat session
 * Backend: GET /api/v1/sessions/{chat_id}/context
 */
export async function getChatContext(
  chatId: string
): Promise<ActionResult<ChatContextResponse>> {
  try {
    const data = await backend.get<ChatContextResponse>(`/sessions/${chatId}/context`);
    const validatedData = ChatContextResponseSchema.parse(data);
    return { success: true, data: validatedData };
  } catch (error) {
    console.error(`[getChatContext] Error for chat ${chatId}:`, error);

    if (error instanceof BackendError) {
      // For 404, return error so chat page can redirect
      if (error.isNotFound()) {
        return {
          success: false,
          error: "Chat session not found",
          code: 404,
        };
      }

      return {
        success: false,
        error: error.message,
        code: error.statusCode,
      };
    }

    if (error instanceof z.ZodError) {
      console.error("[getChatContext] Validation error:", error.errors);
      return { success: false, error: "Invalid response from server" };
    }

    return { success: false, error: "Failed to fetch chat context" };
  }
}

/**
 * Delete a specific chat session
 * Backend: DELETE /api/v1/sessions/{chat_id}
 */
export async function deleteSession(
  chatId: string
): Promise<ActionResult<DeleteSessionResponse>> {
  try {
    const data = await backend.delete<DeleteSessionResponse>(`/sessions/${chatId}`);
    const validatedData = DeleteSessionResponseSchema.parse(data);
    return { success: true, data: validatedData };
  } catch (error) {
    console.error(`[deleteSession] Error for chat ${chatId}:`, error);

    if (error instanceof BackendError) {
      return {
        success: false,
        error: error.message,
        code: error.statusCode,
      };
    }

    if (error instanceof z.ZodError) {
      console.error("[deleteSession] Validation error:", error.errors);
      return { success: false, error: "Invalid response from server" };
    }

    return { success: false, error: "Failed to delete session" };
  }
}

/**
 * Delete all chat sessions
 * Backend: DELETE /api/v1/sessions/
 */
export async function deleteAllSessions(): Promise<ActionResult<DeleteAllSessionsResponse>> {
  try {
    const data = await backend.delete<DeleteAllSessionsResponse>("/sessions/");
    const validatedData = DeleteAllSessionsResponseSchema.parse(data);
    return { success: true, data: validatedData };
  } catch (error) {
    console.error("[deleteAllSessions] Error:", error);

    if (error instanceof BackendError) {
      return {
        success: false,
        error: error.message,
        code: error.statusCode,
      };
    }

    if (error instanceof z.ZodError) {
      console.error("[deleteAllSessions] Validation error:", error.errors);
      return { success: false, error: "Invalid response from server" };
    }

    return { success: false, error: "Failed to delete all sessions" };
  }
}
