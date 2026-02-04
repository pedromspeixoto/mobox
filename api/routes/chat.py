"""Chat API routes - handles agent execution and SSE streaming."""
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db, AsyncSessionLocal
from core.agents import load_agent_config, get_agent_env_vars
from core.sandbox import get_sandbox_client
from shared.events import EventType, get_parser
from core.event_formatters import get_formatter
from core.logging import get_logger

# Map normalized EventType to agent event type for ChatEvent persistence (audit trail)
_CHAT_EVENT_PERSIST: dict[EventType, str] = {
    EventType.TOOL_USE_START: "tool_use",
    EventType.TOOL_RESULT: "tool_result",
    EventType.RESULT: "result",
    EventType.ERROR: "error",
    EventType.TODO_CREATE: "todo_create",
    EventType.TODO_UPDATE: "todo_update",
    EventType.TODO_DONE: "todo_done",
}
from models.chat import CHAT_TITLE_PLACEHOLDER, ChatSession, ChatMessage, ChatEvent, ChatUsage
from routes.schemas.chat import ChatRequest

router = APIRouter()
logger = get_logger(__name__)

async def get_or_create_session(
    db: AsyncSession,
    session_id: str | None,
    agent_id: str,
    agent_name: str,
    prompt: str
) -> tuple[ChatSession, bool]:
    """Get existing session or create a new one."""
    if session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if session and session.title == CHAT_TITLE_PLACEHOLDER:
            title = prompt[:50] + "..." if len(prompt) > 50 else prompt
            session.title = title
            await db.commit()

        if session:
            return session, False
    
    new_id = session_id or str(uuid.uuid4())
    title = prompt[:50] + "..." if len(prompt) > 50 else prompt    

    session = ChatSession(
        id=new_id,
        title=title,
        agent_id=agent_id,
        agent_name=agent_name,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    logger.info(f"Created new session {new_id} for agent {agent_id} ({agent_name})")
    return session, True

@router.post("/")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Execute agent and stream response via SSE."""
    # Determine agent_id: from existing session or from request
    agent_id: str | None = None
    is_new = True

    if request.session_id:
        # Try to get existing session
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == request.session_id)
        )
        existing_session = result.scalar_one_or_none()

        if existing_session:
            # Use agent from existing session
            agent_id = existing_session.agent_id
            is_new = False
            logger.info(f"Using agent '{agent_id}' from existing session {request.session_id}")
        else:
            # Session ID provided but doesn't exist - treat as new session
            if not request.agent_id:
                raise HTTPException(
                    status_code=400,
                    detail="agent_id is required when creating a new session"
                )
            agent_id = request.agent_id
    else:
        # No session_id provided - new session
        if not request.agent_id:
            raise HTTPException(
                status_code=400,
                detail="agent_id is required when creating a new session"
            )
        agent_id = request.agent_id

    # Load agent config
    agent_config = load_agent_config(agent_id)
    if not agent_config:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    if not agent_config.image:
        raise HTTPException(status_code=400, detail=f"Agent '{agent_id}' has no image configured")

    # Get or create session
    session, _ = await get_or_create_session(
        db, request.session_id, agent_id, agent_config.name, request.prompt
    )
    session_id = str(session.id)

    # Save user message IMMEDIATELY (before any other validation)
    user_message = ChatMessage(
        id=str(uuid.uuid4()),
        chat_id=session_id,
        role="user",
        content=request.prompt,
    )
    db.add(user_message)

    session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()

    logger.info(f"Saved user message to session {session_id}")

    # NOW check env vars (after message is saved)
    env_vars = get_agent_env_vars(agent_config)
    if not env_vars:
        logger.error(f"Missing env vars for agent {agent_id}: {agent_config.env_vars}")
        raise HTTPException(
            status_code=500,
            detail="Service temporarily unavailable"
        )

    # Fetch conversation history if this is an existing session
    history_json = None
    if not is_new:
        # Get previous messages for context
        messages_result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.chat_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = messages_result.scalars().all()

        if messages:
            # Format as simple list of {role, content} objects
            history_data = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]
            history_json = json.dumps(history_data, indent=2)
            logger.info(f"Loaded {len(messages)} messages as history for session {session_id}")

    # Shared state for collecting data during streaming (will be saved in background task)
    parser = get_parser(agent_config.framework)
    formatter = get_formatter(
        session_id=session_id,
        agent_id=agent_id,
        is_new_session=is_new,
    )
    stream_state = {
        "accumulated_status": [],
        "accumulated_todos": [],
        "sdk_session_id": None,
        "events_to_save": [],
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        },
        "parser": parser,
        "formatter": formatter,
    }

    async def save_assistant_message():
        """Background task to save assistant message after streaming completes."""
        try:
            async with AsyncSessionLocal() as save_db:
                # Save collected events
                for event in stream_state["events_to_save"]:
                    save_db.add(event)

                # Get content from parser (accumulated during stream)
                parser = stream_state["parser"]
                content = parser.get_text() if parser else ""
                thinking = parser.get_thinking() if parser else ""

                # Build message metadata
                message_metadata = {}
                if stream_state["accumulated_status"]:
                    message_metadata["processing"] = stream_state["accumulated_status"]
                if thinking:
                    message_metadata["thinking"] = thinking
                if stream_state.get("accumulated_todos"):
                    message_metadata["todos"] = stream_state["accumulated_todos"]

                if content or stream_state["accumulated_status"] or thinking or stream_state.get("accumulated_todos"):
                    assistant_message = ChatMessage(
                        id=str(uuid.uuid4()),
                        chat_id=session_id,
                        role="assistant",
                        content=content or "",
                        message_metadata=message_metadata if message_metadata else None,
                    )
                    save_db.add(assistant_message)
                    logger.info(f"Saving assistant message to session {session_id}: {len(content or '')} chars")

                # Save usage to ChatUsage for context/usage display (aggregated by get_chat_context)
                u = stream_state.get("usage", {})
                if u.get("total_tokens", 0) > 0 or u.get("cost_usd", 0) > 0:
                    chat_usage = ChatUsage(
                        id=str(uuid.uuid4()),
                        chat_id=session_id,
                        input_tokens=u.get("input_tokens", 0),
                        output_tokens=u.get("output_tokens", 0),
                        total_tokens=u.get("total_tokens", 0),
                        cost_usd=u.get("cost_usd", 0.0),
                    )
                    save_db.add(chat_usage)
                    logger.info(f"Saved usage for session {session_id}: {u.get('total_tokens', 0)} tokens, ${u.get('cost_usd', 0):.6f}")

                # Save SDK session ID
                final_sdk_id = stream_state["sdk_session_id"]
                if parser:
                    final_sdk_id = final_sdk_id or parser.get_sdk_session_id()
                if final_sdk_id:
                    result = await save_db.execute(
                        select(ChatSession).where(ChatSession.id == session_id)
                    )
                    session_obj = result.scalar_one_or_none()
                    if session_obj and session_obj.sdk_session_id != final_sdk_id:
                        session_obj.sdk_session_id = final_sdk_id
                        logger.info(f"Saved SDK session ID {final_sdk_id} for session {session_id}")

                await save_db.commit()
                logger.info(f"Successfully committed assistant message to session {session_id}")
        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}", exc_info=True)

    async def generate_stream():
        """Generate SSE stream from agent execution."""
        parser = stream_state["parser"]
        formatter = stream_state["formatter"]

        try:
            # Send start
            for evt in formatter.start():
                yield evt

            sandbox = get_sandbox_client()
            logger.info(f"Starting sandbox.run_agent() for session {session_id}")
            async for agent_event in sandbox.run_agent(
                session_id=session_id,
                image_url=agent_config.image,
                agent_id=agent_id,
                prompt=request.prompt,
                env_vars=env_vars,
                command=agent_config.command,
                timeout=agent_config.timeout,
                idle_timeout=agent_config.idle_timeout,
                history=history_json,
            ):
                # Parse: agents emit events → shared parser normalizes (single source of truth)
                raw = {"type": agent_event.type, "data": agent_event.data}
                event = parser.parse(raw)
                logger.debug(f"Parsed agent event: {agent_event.type} → {event.type.value}")

                # Collect from normalized event only (no raw agent_event logic)
                if event.type == EventType.STATUS:
                    status_msg = event.data.get("message", "")
                    if status_msg:
                        stream_state["accumulated_status"].append(status_msg)

                elif event.type == EventType.TODO_CREATE:
                    items = event.data.get("items", [])
                    if items:
                        stream_state["accumulated_status"].append(f"Planning: {len(items)} tasks")
                        stream_state["accumulated_todos"] = items

                elif event.type == EventType.TODO_UPDATE:
                    items = event.data.get("items", [])
                    if items:
                        stream_state["accumulated_status"].append(f"Updated: {len(items)} tasks")
                        stream_state["accumulated_todos"] = items

                elif event.type == EventType.TODO_DONE:
                    item = event.data.get("item", {})
                    index = event.data.get("index", 0)
                    content = item.get("content", "Task")[:50]
                    stream_state["accumulated_status"].append(f"Completed: {content}...")
                    # Update accumulated_todos so final state is saved
                    todos = list(stream_state.get("accumulated_todos", []))
                    if 0 <= index < len(todos):
                        todos[index] = {**todos[index], "status": "completed", **item}
                        stream_state["accumulated_todos"] = todos

                elif event.type == EventType.USAGE:
                    usage = event.data.get("usage", {})
                    if isinstance(usage, dict):
                        u = stream_state["usage"]
                        inp = int(usage.get("input_tokens", 0))
                        out_tok = int(usage.get("output_tokens", 0))
                        total = usage.get("total_tokens")
                        if event.data.get("total"):
                            u["input_tokens"] = inp
                            u["output_tokens"] = out_tok
                            u["total_tokens"] = int(total) if total is not None else inp + out_tok
                        else:
                            u["input_tokens"] += inp
                            u["output_tokens"] += out_tok
                            u["total_tokens"] = u["input_tokens"] + u["output_tokens"]

                elif event.type == EventType.RESULT:
                    data = event.data
                    for key in ("session_id", "sessionId"):
                        if key in data and data[key]:
                            stream_state["sdk_session_id"] = str(data[key])
                            break
                    cost = data.get("total_cost_usd")
                    if cost is not None:
                        stream_state["usage"]["cost_usd"] = float(cost)
                    usage = data.get("usage")
                    if isinstance(usage, dict):
                        u = stream_state["usage"]
                        u["input_tokens"] = int(usage.get("input_tokens", u["input_tokens"]))
                        u["output_tokens"] = int(usage.get("output_tokens", u["output_tokens"]))
                        u["total_tokens"] = int(usage.get("total_tokens", u["input_tokens"] + u["output_tokens"]))

                # Persist from normalized event (formatter is single source of truth)
                if event.type in _CHAT_EVENT_PERSIST:
                    agent_type = _CHAT_EVENT_PERSIST[event.type]
                    event_name = event.data.get("name") if event.type == EventType.TOOL_USE_START else None
                    stream_state["events_to_save"].append(ChatEvent(
                        id=str(uuid.uuid4()),
                        chat_id=session_id,
                        event_type=agent_type,
                        event_name=event_name,
                        event_data=event.data,
                    ))

                # Convert to AI SDK format and yield
                for formatted in formatter.format(event):
                    yield formatted

                if event.type == EventType.DONE:
                    break

            # Send end
            for evt in formatter.end():
                yield evt

        except Exception as e:
            logger.error(f"Agent execution error: {e}", exc_info=True)

            error_event = parser.parse({"type": "error", "data": {"message": str(e)}})
            for evt in formatter.format(error_event):
                yield evt
            for evt in formatter.end():
                yield evt

            if error_event.type in _CHAT_EVENT_PERSIST:
                stream_state["events_to_save"].append(ChatEvent(
                    id=str(uuid.uuid4()),
                    chat_id=session_id,
                    event_type=_CHAT_EVENT_PERSIST[error_event.type],
                    event_data=error_event.data,
                ))

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
            "x-vercel-ai-ui-message-stream": "v1",
        },
        background=BackgroundTask(save_assistant_message),
    )
