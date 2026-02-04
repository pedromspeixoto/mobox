# Stream Resumption

> **Reference**: [AI SDK - Chatbot Resume Streams](https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-resume-streams)

Mobox implements stream resumption following the AI SDK pattern so streams survive page refresh and client disconnects.

## How It Works

1. **Stream creation**: POST creates a resumable stream via `resumable-stream`, stores `sessionId → streamId` in Redis, returns the stream.
2. **Stream tracking**: Redis holds the active stream ID per chat.
3. **Client reconnection**: On mount, `useChat({ resume: true })` sends GET to `/api/chat/[id]/stream`.
4. **Stream recovery**: GET handler looks up `streamId`, calls `resumeExistingStream(streamId)`, returns the stream or 204 if none.
5. **Completion**: Stream ID expires via TTL; `resumeExistingStream` returns `null` when done.

## Prerequisites (from AI SDK docs)

- [resumable-stream](https://www.npmjs.com/package/resumable-stream)
- Redis instance
- Persistence for session → stream ID (Mobox uses Redis)

## Mobox Implementation

**Difference from canonical example**: Mobox proxies to a Python backend instead of using `streamText`. The POST handler pipes the backend SSE stream through `createNewResumableStream` instead of using `consumeSseStream`.

### Setup

1. Redis in docker-compose
2. `REDIS_URL=redis://localhost:6379` in frontend `.env`
3. `docker compose up -d redis`

### Files

| File | Role |
|------|------|
| `frontend/lib/stream-store.ts` | Redis session → streamId mapping |
| `frontend/app/(chat)/api/chat/route.ts` | POST: resumable stream when REDIS_URL set |
| `frontend/app/(chat)/api/chat/[id]/stream/route.ts` | GET: resume or 204 |
| `frontend/components/chat.tsx` | `useChat({ id, resume: true })` |

### Behavior

- **Without REDIS_URL**: Direct proxy (no resumption)
- **With REDIS_URL**: Resumable streams; refresh reconnects via GET

## Important (from AI SDK docs)

- **Abort incompatibility**: `resume: true` conflicts with abort. See [troubleshooting](https://ai-sdk.dev/docs/troubleshooting/abort-breaks-resumable-streams).
- **Stream expiration**: Streams expire in Redis (resumable-stream default).
- **Race conditions**: Clear previous `activeStreamId` when starting a new stream.
