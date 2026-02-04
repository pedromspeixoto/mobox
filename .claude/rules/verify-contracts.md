# Verify API Contracts

**CRITICAL**: Always verify when modifying API endpoints, server actions, or data fetching code.

## Purpose

Ensure type safety between Python backend (Pydantic) and TypeScript frontend (Zod) by verifying API contracts are aligned.

## Files to Compare

- **Backend schemas**: `api/routes/schemas/*.py`
- **Frontend contracts**: `frontend/lib/api/contracts.ts`

## Schema Mapping

| Frontend (Zod)                    | Backend (Pydantic)               | Endpoint                          |
|-----------------------------------|----------------------------------|-----------------------------------|
| `ChatSessionResponseSchema`       | `ChatSessionResponse`            | `GET /sessions/`                  |
| `ChatMessageResponseSchema`       | `ChatMessageResponse`            | (nested)                          |
| `PaginatedMessagesResponseSchema` | `PaginatedMessagesResponse`      | `GET /sessions/{id}/messages`     |
| `ChatRequestSchema`               | `ChatRequest`                    | `POST /chat/`                     |
| `ChatContextResponseSchema`       | `ChatContextResponse`            | `GET /sessions/{id}/context`      |
| `DeleteSessionResponseSchema`     | `DeleteSessionResponse`          | `DELETE /sessions/{id}`           |
| `DeleteAllSessionsResponseSchema` | `DeleteAllSessionsResponse`      | `DELETE /sessions/`               |

## Type Equivalents

| Python (Pydantic)    | TypeScript (Zod)              |
|----------------------|-------------------------------|
| `str`                | `z.string()`                  |
| `int`                | `z.number().int()`            |
| `float`              | `z.number()`                  |
| `bool`               | `z.boolean()`                 |
| `Optional[T]`        | `z.T().nullable().optional()` |
| `List[T]`            | `z.array(T)`                  |
| `Dict[str, Any]`     | `z.record(z.unknown())`       |

## Verification Checklist

1. Field names match exactly (both use snake_case)
2. Field types are equivalent
3. Validation constraints match (`min_length` → `.min()`, `ge=0` → `.nonnegative()`)
4. Default values match
5. Optional markers match (`Optional[str]` → `.nullable().optional()`)

## When Changing APIs

1. Update backend Pydantic schema in `api/routes/schemas/`
2. Update frontend Zod schema in `frontend/lib/api/contracts.ts`
3. Update server actions in `frontend/app/(chat)/actions/` if needed
4. Run `pnpm build` in frontend to catch type errors
5. Test the integration
