/**
 * Type exports for server actions
 * Separated from server actions files because "use server" can't export types
 */

import { z } from "zod";
import {
  ChatSessionResponseSchema,
  ChatMessageResponseSchema,
  PaginatedMessagesResponseSchema,
  ChatContextResponseSchema,
  AgentResponseSchema,
  type ChatSessionResponse,
  type PaginatedMessagesResponse,
  type ChatContextResponse,
  type AgentResponse,
} from "@/lib/api/contracts";

// Session types
export type ChatSession = ChatSessionResponse;
export type ChatContext = ChatContextResponse;
export type ChatMessage = z.infer<typeof ChatMessageResponseSchema>;
export type { PaginatedMessagesResponse };

// Agent types
export type Agent = AgentResponse;

// Re-export schemas for client-side validation
export const chatSessionSchema = ChatSessionResponseSchema;
export const chatMessageSchema = ChatMessageResponseSchema;
export const paginatedMessagesResponseSchema = PaginatedMessagesResponseSchema;
export const chatContextSchema = ChatContextResponseSchema;
export const agentSchema = AgentResponseSchema;

// Result type for server actions
export type ActionResult<T> =
  | { success: true; data: T }
  | { success: false; error: string; code?: number };
