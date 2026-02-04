"use server";

import { cookies } from "next/headers";

/**
 * Save the selected agent as a cookie (for remembering user preference)
 */
export async function saveAgentPreferenceCookie(agentId: string): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set("preferred-agent", agentId, {
    maxAge: 60 * 60 * 24 * 365, // 1 year
  });
}

/**
 * Generate a title from the user's first message
 * TODO: Implement AI-based title generation
 */
export async function generateTitleFromUserMessage(_params: {
  message: unknown;
}): Promise<string> {
  return "New Chat";
}

/**
 * Update chat visibility (public/private)
 * TODO: Implement when visibility feature is added
 */
export async function updateChatVisibility(_params: {
  chatId: string;
  visibility: "public" | "private";
}): Promise<void> {
  // No-op in simplified version
}

/**
 * Delete trailing messages after a specific message
 * TODO: Implement when message editing is supported
 */
export async function deleteTrailingMessages(_params: {
  chatId: string;
  messageId: string;
}): Promise<void> {
  // No-op in simplified version
}
