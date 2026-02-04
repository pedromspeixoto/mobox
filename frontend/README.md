# Frontend

Next.js 16 application with React 19, using Server Actions for data fetching.

## Architecture

```
frontend/
├── app/(chat)/
│   ├── actions/           # Server Actions (data fetching & mutations)
│   │   ├── sessions.ts    # Session CRUD: getSessions, getMessages, deleteSession
│   │   └── chat.ts        # Chat utilities: saveChatModelAsCookie
│   ├── api/chat/          # API route for SSE streaming (can't use server actions)
│   └── chat/[chatId]/     # Chat page
├── components/            # React components
├── lib/api/
│   ├── backend.ts         # Backend API client (server-only)
│   └── contracts.ts       # Zod schemas matching backend Pydantic models
└── contexts/              # React contexts
```

## Data Flow

1. **Server Actions** (`app/(chat)/actions/`) handle all data operations
2. **Backend client** (`lib/api/backend.ts`) communicates with the Python API
3. **Streaming** uses API route (`api/chat/route.ts`) since Server Actions don't support SSE

## Type Safety

Types are defined in `lib/api/contracts.ts` using Zod schemas that mirror the backend Pydantic models:

| Frontend (Zod)              | Backend (Pydantic)           | Endpoint                          |
|-----------------------------|------------------------------|-----------------------------------|
| `ChatSessionResponseSchema` | `ChatSessionResponse`        | `GET /sessions/`                  |
| `PaginatedMessagesResponseSchema` | `PaginatedMessagesResponse` | `GET /sessions/{id}/messages` |
| `ChatContextResponseSchema` | `ChatContextResponse`        | `GET /sessions/{id}/context`      |
| `ChatRequestSchema`         | `ChatRequest`                | `POST /chat/`                     |
| `DeleteSessionResponseSchema` | `DeleteSessionResponse`    | `DELETE /sessions/{id}`           |

All responses are validated at runtime with Zod. If the backend schema changes, update `contracts.ts`.

## Key Patterns

- **Server Actions** for mutations and data fetching (Next.js best practice)
- **API routes** only for streaming responses
- **`server-only`** package prevents accidental client imports of server code
- **Zod validation** ensures type safety between Python and TypeScript

## Usage

```tsx
// In components - call server actions directly
import { getSessions, deleteSession, getAgents } from "@/app/(chat)/actions";

const result = await getSessions();
if (result.success) {
  // result.data is typed as ChatSessionResponse[]
}
```

## New Chat Flow

1. User clicks "New Chat" → `AgentSelectModal` opens
2. User selects an agent → `POST /sessions/` creates session with `agent_id` and `agent_name`
3. Navigate to `/chat/{sessionId}` with session already in database
4. Agent displayed in chat header (from session data via `/sessions/{id}/context`)

## Development

```bash
pnpm install
pnpm dev        # runs on port 1337
```

Requires backend running at `http://localhost:8080` (configurable via `BACKEND_URL` env var).
