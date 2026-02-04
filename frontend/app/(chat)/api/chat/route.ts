import { after } from "next/server";
import { createResumableStreamContext } from "resumable-stream";
import { UI_MESSAGE_STREAM_HEADERS } from "ai";
import { ChatSDKError } from "@/lib/errors";
import type { ChatMessage } from "@/lib/types";
import { type PostRequestBody, postRequestBodySchema } from "@/app/(chat)/api/chat/schema";
import { backend, BackendError } from "@/lib/api/backend";
import { type ChatRequest } from "@/lib/api/contracts";
import {
  setActiveStream,
  clearActiveStream,
  isResumableEnabled,
} from "@/lib/stream-store";

export const maxDuration = 60;

function getStreamContext() {
  return createResumableStreamContext({
    waitUntil: after,
  });
}

/**
 * Chat streaming endpoint
 * Transforms frontend message format to backend ChatRequest format
 *
 * Frontend sends: { id, message: { parts: [...] }, agentId }
 * Backend expects: { prompt, session_id, agent_id }
 */
export async function POST(request: Request) {
  let requestBody: PostRequestBody;

  console.log("[POST /api/chat] Received request");

  try {
    const json = await request.json();
    requestBody = postRequestBodySchema.parse(json);
    console.log("[POST /api/chat] Request body parsed:", {
      chatId: requestBody.id,
      messageId: requestBody.message?.id,
      agentId: requestBody.agentId,
    });
  } catch (error) {
    console.error("[POST /api/chat] Failed to parse request body:", {
      error: error instanceof Error ? error.message : String(error),
    });
    return new ChatSDKError("bad_request:api").toResponse();
  }

  try {
    const { message }: { message: ChatMessage } = requestBody;

    // Extract text content from message parts
    const textParts = message.parts
      .filter((part) => part.type === "text")
      .map((part) => (part as { type: "text"; text: string }).text);

    if (textParts.length === 0) {
      return new ChatSDKError("bad_request:api").toResponse();
    }

    const prompt = textParts.join("\n");
    const sessionId = requestBody.id;
    const agentId = requestBody.agentId;

    if (!sessionId) {
      return new ChatSDKError("bad_request:api", "Session ID is required.").toResponse();
    }

    // Build backend request matching ChatRequest schema
    // Only include agent_id for new sessions (when frontend provides it)
    // Backend will fetch agent from session DB for existing sessions
    const chatRequest: ChatRequest = {
      prompt,
      session_id: sessionId,
      ...(agentId && { agent_id: agentId }),
    };

    // Stream response from backend
    const backendResponse = await backend.fetch("/chat/", {
      method: "POST",
      body: JSON.stringify(chatRequest),
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      console.error("[POST /api/chat] Backend request failed:", {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        error: errorText,
      });

      // Try to parse error message from backend
      let errorMessage = `Server error (${backendResponse.status})`;
      try {
        const errorJson = JSON.parse(errorText);
        if (errorJson.detail) {
          errorMessage = errorJson.detail;
        }
      } catch {
        // If not JSON, use text directly if it's meaningful
        if (errorText && errorText.length < 200) {
          errorMessage = errorText;
        }
      }

      return new ChatSDKError("offline:chat", errorMessage).toResponse();
    }

    if (!backendResponse.body) {
      return new ChatSDKError("offline:chat").toResponse();
    }

    if (isResumableEnabled()) {
      const streamId = crypto.randomUUID();
      await clearActiveStream(sessionId);
      await setActiveStream(sessionId, streamId);

      const resumableStream = await getStreamContext().createNewResumableStream(
        streamId,
        () =>
          backendResponse.body!.pipeThrough(new TextDecoderStream())
      );

      return new Response(resumableStream, {
        headers: {
          ...UI_MESSAGE_STREAM_HEADERS,
          "Cache-Control": "no-cache",
        },
      });
    }

    return new Response(backendResponse.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "x-vercel-ai-ui-message-stream": "v1",
      },
    });
  } catch (error) {
    if (error instanceof ChatSDKError) {
      return error.toResponse();
    }

    if (error instanceof BackendError) {
      console.error("[POST /api/chat] Backend unavailable:", error.message);
      return new ChatSDKError("offline:chat", error.message).toResponse();
    }

    console.error("Unhandled error in chat API:", error);
    return new ChatSDKError("offline:chat").toResponse();
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");

  if (!id) {
    return new ChatSDKError("bad_request:api").toResponse();
  }

  return Response.json({ id }, { status: 200 });
}
