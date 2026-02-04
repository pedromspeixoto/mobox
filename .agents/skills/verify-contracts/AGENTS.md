# Verify API Contracts

**Priority: CRITICAL** - Always verify when touching API code.

When modifying any API endpoint, server action, or data fetching code, you MUST verify that the frontend TypeScript types (Zod schemas in `frontend/lib/api/contracts.ts`) match the backend Python types (Pydantic schemas in `api/routes/schemas/`).

Read `SKILL.md` in this directory for the full verification checklist.

## Quick Check

1. Read `api/routes/schemas/*.py` for backend types
2. Read `frontend/lib/api/contracts.ts` for frontend types  
3. Ensure field names, types, and constraints match exactly
4. Update frontend contracts if backend changed (or vice versa)
