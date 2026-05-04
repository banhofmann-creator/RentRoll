"""AI chatbot API with Claude tool use."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.core.chat_tools import TOOL_DEFINITIONS, WRITE_TOOLS, execute_tool
from app.database import get_db
from app.models.database import ChatMessage, ChatSession

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = """\
You are a data assistant for the RentRoll application, which manages GARBE-format \
commercial real estate rent rolls and transforms them into BVI-compliant exports.

You help users:
- Query and explore rent roll data (tenants, properties, rents, areas, leases)
- Understand and resolve data quality issues (unmapped tenants/funds, aggregation mismatches)
- Edit master data (tenant, property, fund mappings) — these edits require user confirmation
- Compare reporting periods and analyze trends
- Explain the data transformation pipeline

Key domain knowledge:
- LEERSTAND = vacancy (empty space). Excluded from tenant counts.
- Stellplätze = parking spaces. Often excluded from area calculations.
- WAULT = Weighted Average Unexpired Lease Term.
- BVI = German investment fund reporting standard.
- Stichtag = reporting date (cutoff date for the data).
- Properties are identified by numeric IDs (e.g. "7042").
- Funds are identified by codes (e.g. "GLIF", "GLIFPLUSII").

When making edits (update_tenant, update_property, update_fund_mapping, resolve_inconsistency), \
explain what you're about to change and why before calling the tool.

Keep responses concise and use tables/formatting when showing data.
Respond in the same language as the user's message.
"""


class ChatRequest(BaseModel):
    session_id: int | None = None
    message: str
    confirmed_tool_calls: list[str] | None = None


class ChatMessageOut(BaseModel):
    role: str
    content: str
    tool_calls: list[dict] | None = None
    created_at: str


class SessionOut(BaseModel):
    id: int
    title: str | None
    created_at: str
    last_message_at: str | None


class PendingConfirmation(BaseModel):
    tool_name: str
    tool_input: dict
    tool_use_id: str
    description: str


class ChatResponse(BaseModel):
    session_id: int
    message: str
    pending_confirmations: list[PendingConfirmation]
    tool_results: list[dict]


def _get_client():
    if not settings.anthropic_api_key:
        raise HTTPException(503, "Anthropic API key not configured. Set ANTHROPIC_API_KEY in .env")
    import anthropic
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _build_messages(db: Session, session: ChatSession, new_message: str) -> list[dict]:
    """Build the message history for the Claude API call."""
    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )

    messages = []
    for msg in history:
        if msg.role == "user":
            messages.append({"role": "user", "content": msg.content})
        elif msg.role == "assistant":
            content_parts = []
            if msg.content:
                content_parts.append({"type": "text", "text": msg.content})
            if msg.tool_calls_json:
                for tc in msg.tool_calls_json:
                    if tc.get("type") == "tool_use":
                        content_parts.append(tc)
                    elif tc.get("type") == "tool_result":
                        pass
            if content_parts:
                messages.append({"role": "assistant", "content": content_parts})
        elif msg.role == "tool_result":
            if msg.tool_calls_json:
                messages.append({"role": "user", "content": msg.tool_calls_json})

    messages.append({"role": "user", "content": new_message})
    return messages


def _describe_write_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "update_tenant":
        fields = {k: v for k, v in tool_input.items() if k != "tenant_id" and v is not None}
        return f"Update tenant #{tool_input.get('tenant_id')}: set {fields}"
    elif tool_name == "update_property":
        return f"Update property {tool_input.get('property_id')}: set {tool_input.get('fields', {})}"
    elif tool_name == "update_fund_mapping":
        fields = {k: v for k, v in tool_input.items() if k != "csv_fund_name" and v is not None}
        return f"Update fund '{tool_input.get('csv_fund_name')}': set {fields}"
    elif tool_name == "resolve_inconsistency":
        return f"Resolve inconsistency #{tool_input.get('inconsistency_id')} as '{tool_input.get('status')}'"
    return f"Execute {tool_name} with {tool_input}"


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(db: Session = Depends(get_db)):
    sessions = (
        db.query(ChatSession)
        .order_by(ChatSession.last_message_at.desc().nullsfirst())
        .limit(50)
        .all()
    )
    return [
        SessionOut(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            last_message_at=s.last_message_at.isoformat() if s.last_message_at else None,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageOut])
def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        ChatMessageOut(
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls_json,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.post("/message", response_model=ChatResponse)
def send_message(req: ChatRequest, db: Session = Depends(get_db)):
    client = _get_client()

    if req.session_id:
        session = db.get(ChatSession, req.session_id)
        if not session:
            raise HTTPException(404, "Session not found")
    else:
        session = ChatSession(title=req.message[:100])
        db.add(session)
        db.commit()
        db.refresh(session)

    confirmed = set(req.confirmed_tool_calls or [])

    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)
    session.last_message_at = datetime.now(timezone.utc)
    db.commit()

    messages = _build_messages(db, session, req.message)

    pending_confirmations = []
    tool_results_out = []
    final_text = ""

    for _ in range(10):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        text_parts = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        current_text = "\n".join(text_parts)
        if current_text:
            final_text += ("\n" if final_text else "") + current_text

        if not tool_uses:
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=final_text,
                tool_calls_json=[{"type": "text", "text": current_text}] if current_text else None,
            )
            db.add(assistant_msg)
            db.commit()
            break

        assistant_content = []
        if current_text:
            assistant_content.append({"type": "text", "text": current_text})

        tool_result_content = []
        needs_confirmation = []

        for tu in tool_uses:
            tool_block = {
                "type": "tool_use",
                "id": tu.id,
                "name": tu.name,
                "input": tu.input,
            }
            assistant_content.append(tool_block)

            if tu.name in WRITE_TOOLS and tu.id not in confirmed:
                needs_confirmation.append(
                    PendingConfirmation(
                        tool_name=tu.name,
                        tool_input=tu.input,
                        tool_use_id=tu.id,
                        description=_describe_write_tool(tu.name, tu.input),
                    )
                )
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": "PENDING USER CONFIRMATION — do not proceed with this action yet.",
                })
            else:
                result = execute_tool(db, tu.name, tu.input)
                tool_results_out.append({"tool": tu.name, "input": tu.input, "result": result})
                tool_result_content.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result),
                })

        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=current_text,
            tool_calls_json=assistant_content,
        )
        db.add(assistant_msg)

        tool_result_msg = ChatMessage(
            session_id=session.id,
            role="tool_result",
            content="",
            tool_calls_json=tool_result_content,
        )
        db.add(tool_result_msg)
        db.commit()

        if needs_confirmation:
            pending_confirmations.extend(needs_confirmation)
            break

        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_result_content})

    return ChatResponse(
        session_id=session.id,
        message=final_text,
        pending_confirmations=pending_confirmations,
        tool_results=tool_results_out,
    )
