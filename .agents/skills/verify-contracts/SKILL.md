# Verify API Contracts

**ALWAYS run this verification when modifying API endpoints or data fetching code.**

## Purpose

Ensure type safety between the Python backend (Pydantic) and TypeScript frontend (Zod) by verifying that API contracts are aligned.

## When to Verify

Run this verification when:
- Adding or modifying backend API endpoints
- Adding or modifying frontend server actions
- Changing request/response schemas in either codebase
- Debugging API integration issues

## Verification Steps

### 1. Compare Backend Pydantic Schemas

Check the backend schemas at `api/routes/schemas/`:

```
api/routes/schemas/
├── __init__.py      # All exports
├── session.py       # ChatSessionResponse
├── message.py       # ChatMessageResponse, PaginatedMessagesResponse
├── chat.py          # ChatRequest, EventFormat
├── usage.py         # ChatContextResponse
└── delete.py        # DeleteSessionResponse, DeleteAllSessionsResponse
```

### 2. Compare Frontend Zod Schemas

Check the frontend contracts at `frontend/lib/api/contracts.ts`:

| Frontend Schema                   | Backend Schema               | Endpoint                     |
|-----------------------------------|------------------------------|------------------------------|
| `ChatSessionResponseSchema`       | `ChatSessionResponse`        | `GET /sessions/`             |
| `ChatMessageResponseSchema`       | `ChatMessageResponse`        | (nested in paginated)        |
| `PaginatedMessagesResponseSchema` | `PaginatedMessagesResponse`  | `GET /sessions/{id}/messages`|
| `ChatRequestSchema`               | `ChatRequest`                | `POST /chat/`                |
| `ChatContextResponseSchema`       | `ChatContextResponse`        | `GET /sessions/{id}/context` |
| `DeleteSessionResponseSchema`     | `DeleteSessionResponse`      | `DELETE /sessions/{id}`      |
| `DeleteAllSessionsResponseSchema` | `DeleteAllSessionsResponse`  | `DELETE /sessions/`          |

### 3. Field-by-Field Comparison

For each schema, verify:

1. **Field names match exactly** (Python snake_case = TypeScript snake_case)
2. **Field types are equivalent**:
   - `str` → `z.string()`
   - `int` → `z.number().int()`
   - `float` → `z.number()`
   - `bool` → `z.boolean()`
   - `Optional[T]` → `z.T().nullable().optional()`
   - `List[T]` → `z.array(T)`
   - `Dict[str, Any]` → `z.record(z.unknown())`
3. **Validation constraints match**:
   - `min_length=1` → `.min(1)`
   - `ge=0` → `.nonnegative()` or `.min(0)`
   - `le=100` → `.max(100)`
4. **Default values match**

### 4. Verify API Route Parameters

Check `frontend/app/(chat)/api/chat/route.ts` sends correct fields to backend:

```typescript
// Must match ChatRequest schema exactly
const chatRequest: ChatRequest = {
  prompt,           // required string
  session_id,       // optional UUID
  agent_id,         // default "hello-world"
  event_format,     // "ai_sdk" | "raw"
};
```

## Quick Verification Command

Read both files and compare:

```bash
# Backend schemas
cat api/routes/schemas/session.py
cat api/routes/schemas/message.py
cat api/routes/schemas/chat.py
cat api/routes/schemas/usage.py
cat api/routes/schemas/delete.py

# Frontend contracts
cat frontend/lib/api/contracts.ts
```

## Common Issues

1. **Field name mismatch**: Backend uses `chat_id`, frontend uses `chatId`
2. **Missing optional marker**: Backend has `Optional[str]`, frontend missing `.nullable()`
3. **Wrong default value**: Backend defaults to `"gpt-4o"`, frontend defaults to `"claude"`
4. **New field not added**: Backend added field, frontend schema not updated

## After Making Changes

1. Update `frontend/lib/api/contracts.ts` to match backend
2. Update server actions in `frontend/app/(chat)/actions/sessions.ts`
3. Run `pnpm build` in frontend to catch type errors
4. Test the integration manually
