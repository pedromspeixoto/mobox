import { after } from "next/server";
import { createResumableStreamContext } from "resumable-stream";
import { UI_MESSAGE_STREAM_HEADERS } from "ai";
import { getActiveStream, isResumableEnabled } from "@/lib/stream-store";

function getStreamContext() {
  return createResumableStreamContext({
    waitUntil: after,
  });
}

/**
 * GET /api/chat/[id]/stream
 * Resume an active stream after client disconnect (e.g. page refresh).
 * Returns 204 No Content if no active stream exists.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: sessionId } = await params;

  if (!sessionId) {
    return new Response(null, { status: 400 });
  }

  if (!isResumableEnabled()) {
    return new Response(null, { status: 204 });
  }

  const streamId = await getActiveStream(sessionId);
  if (!streamId) {
    return new Response(null, { status: 204 });
  }

  const stream = await getStreamContext().resumeExistingStream(streamId);
  if (!stream) {
    return new Response(null, { status: 204 });
  }

  return new Response(stream, {
    headers: UI_MESSAGE_STREAM_HEADERS,
  });
}
