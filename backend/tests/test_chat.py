"""Tests for chat API and tool execution."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.core.chat_tools import TOOL_DEFINITIONS, WRITE_TOOLS, execute_tool
from app.models.database import (
    ChatMessage,
    ChatSession,
    CsvUpload,
    DataInconsistency,
    FundMapping,
    PropertyMaster,
    RawRentRoll,
    TenantMaster,
    TenantNameAlias,
)


# ── Tool execution tests (no API mocking needed) ────────────────────

def _setup_upload(db, tenant="Tenant A", fund="GLIF", property_id="7042"):
    upload = CsvUpload(filename="test.csv", status="complete", stichtag=date(2025, 3, 31))
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(RawRentRoll(
        upload_id=upload.id, row_number=1, row_type="data",
        fund=fund, property_id=property_id,
        tenant_name=tenant, unit_type="Halle",
        area_sqm=5000, annual_net_rent=120000,
    ))
    db.add(RawRentRoll(
        upload_id=upload.id, row_number=2, row_type="data",
        fund=fund, property_id=property_id,
        tenant_name="LEERSTAND", unit_type="Büro",
        area_sqm=1000, annual_net_rent=0,
    ))
    db.commit()
    return upload


def test_tool_definitions_valid():
    for tool in TOOL_DEFINITIONS:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool
    assert len(TOOL_DEFINITIONS) == 11
    assert WRITE_TOOLS == {"update_tenant", "update_property", "update_fund_mapping", "resolve_inconsistency"}


def test_query_raw_data(db):
    upload = _setup_upload(db)
    result = execute_tool(db, "query_raw_data", {"upload_id": upload.id})
    assert result["total_matching"] == 2
    assert result["rows_returned"] == 2
    assert result["rows"][0]["tenant_name"] == "Tenant A"


def test_query_raw_data_filter_tenant(db):
    upload = _setup_upload(db)
    result = execute_tool(db, "query_raw_data", {"upload_id": upload.id, "tenant_name": "Tenant"})
    assert result["total_matching"] == 1
    assert result["rows"][0]["tenant_name"] == "Tenant A"


def test_query_raw_data_no_upload(db):
    result = execute_tool(db, "query_raw_data", {})
    assert "error" in result


def test_query_portfolio_summary(db):
    upload = _setup_upload(db)
    result = execute_tool(db, "query_portfolio_summary", {"upload_id": upload.id})
    assert result["total_properties"] == 1
    assert result["total_tenants"] == 1
    assert result["total_annual_rent"] == 120000
    assert result["total_area_sqm"] == 6000
    assert result["vacant_area_sqm"] == 1000
    assert result["vacancy_rate_pct"] == pytest.approx(16.67, abs=0.01)


def test_search_tenants(db):
    tm = TenantMaster(tenant_name_canonical="Acme Corp")
    db.add(tm)
    db.commit()
    db.refresh(tm)
    db.add(TenantNameAlias(tenant_master_id=tm.id, csv_tenant_name="ACME CORPORATION"))
    db.commit()

    result = execute_tool(db, "search_tenants", {"name_pattern": "acme"})
    assert result["count"] == 1
    assert result["tenants"][0]["canonical_name"] == "Acme Corp"
    assert "ACME CORPORATION" in result["tenants"][0]["aliases"]


def test_search_tenants_by_alias(db):
    tm = TenantMaster(tenant_name_canonical="Real Name")
    db.add(tm)
    db.commit()
    db.refresh(tm)
    db.add(TenantNameAlias(tenant_master_id=tm.id, csv_tenant_name="CSV Alias Name"))
    db.commit()

    result = execute_tool(db, "search_tenants", {"name_pattern": "CSV Alias"})
    assert result["count"] == 1
    assert result["tenants"][0]["canonical_name"] == "Real Name"


def test_list_properties(db):
    db.add(PropertyMaster(property_id="7042", city="Almere", country="NL"))
    db.add(PropertyMaster(property_id="1001", city="Hamburg", country="DE"))
    db.commit()

    result = execute_tool(db, "list_properties", {"search": "almere"})
    assert result["count"] == 1
    assert result["properties"][0]["property_id"] == "7042"

    result_all = execute_tool(db, "list_properties", {})
    assert result_all["count"] == 2


def test_list_inconsistencies(db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    db.add(DataInconsistency(
        upload_id=upload.id, category="unmapped_tenant", severity="error",
        entity_type="tenant", entity_id="Unknown Corp",
        description="Unmapped tenant: Unknown Corp", status="open",
    ))
    db.add(DataInconsistency(
        upload_id=upload.id, category="missing_metadata", severity="warning",
        entity_type="property", entity_id="9999",
        description="No metadata for property 9999", status="open",
    ))
    db.commit()

    result = execute_tool(db, "list_inconsistencies", {"category": "unmapped_tenant"})
    assert result["total"] == 1
    assert result["items"][0]["entity_id"] == "Unknown Corp"


def test_update_tenant(db):
    tm = TenantMaster(tenant_name_canonical="Old Name")
    db.add(tm)
    db.commit()
    db.refresh(tm)

    result = execute_tool(db, "update_tenant", {
        "tenant_id": tm.id,
        "tenant_name_canonical": "New Name",
        "nace_sector": "L68",
    })
    assert result["success"] is True
    assert set(result["updated_fields"]) == {"tenant_name_canonical", "nace_sector"}

    db.refresh(tm)
    assert tm.tenant_name_canonical == "New Name"
    assert tm.nace_sector == "L68"


def test_update_tenant_not_found(db):
    result = execute_tool(db, "update_tenant", {"tenant_id": 9999})
    assert "error" in result


def test_update_property(db):
    db.add(PropertyMaster(property_id="7042", city="Almere"))
    db.commit()

    result = execute_tool(db, "update_property", {
        "property_id": "7042",
        "fields": {"city": "Amsterdam", "country": "NL"},
    })
    assert result["success"] is True
    prop = db.query(PropertyMaster).filter(PropertyMaster.property_id == "7042").first()
    assert prop.city == "Amsterdam"
    assert prop.country == "NL"


def test_update_property_invalid_field(db):
    db.add(PropertyMaster(property_id="7042"))
    db.commit()

    result = execute_tool(db, "update_property", {
        "property_id": "7042",
        "fields": {"nonexistent_field": "value"},
    })
    assert "error" in result
    assert "nonexistent_field" in result["error"]


def test_update_fund_mapping(db):
    db.add(FundMapping(csv_fund_name="GLIF", bvi_fund_id=None))
    db.commit()

    result = execute_tool(db, "update_fund_mapping", {
        "csv_fund_name": "GLIF",
        "bvi_fund_id": "DE000GLIF001",
    })
    assert result["success"] is True
    fund = db.query(FundMapping).filter(FundMapping.csv_fund_name == "GLIF").first()
    assert fund.bvi_fund_id == "DE000GLIF001"


def test_resolve_inconsistency(db):
    upload = CsvUpload(filename="test.csv", status="complete")
    db.add(upload)
    db.commit()
    db.refresh(upload)

    inc = DataInconsistency(
        upload_id=upload.id, category="unmapped_tenant", severity="error",
        entity_type="tenant", entity_id="X",
        description="test", status="open",
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    result = execute_tool(db, "resolve_inconsistency", {
        "inconsistency_id": inc.id,
        "status": "acknowledged",
        "resolution_note": "Handled via chatbot",
    })
    assert result["success"] is True
    db.refresh(inc)
    assert inc.status == "acknowledged"
    assert inc.resolved_by == "chatbot"


def test_unknown_tool(db):
    result = execute_tool(db, "nonexistent", {})
    assert "error" in result


# ── API endpoint tests (with mocked Claude) ─────────────────────────

def _mock_claude_response(text="Here is the answer.", tool_uses=None):
    """Create a mock Claude API response."""
    content = []
    if text:
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text
        content.append(text_block)
    if tool_uses:
        for tu in tool_uses:
            block = MagicMock()
            block.type = "tool_use"
            block.id = tu["id"]
            block.name = tu["name"]
            block.input = tu["input"]
            content.append(block)

    response = MagicMock()
    response.content = content
    return response


@patch("app.api.chat._get_client")
def test_chat_creates_session(mock_get_client, client, db):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_claude_response("Hello!")
    mock_get_client.return_value = mock_client

    resp = client.post("/api/chat/message", json={"message": "Hi"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] > 0
    assert "Hello" in data["message"]
    assert data["pending_confirmations"] == []


@patch("app.api.chat._get_client")
def test_chat_read_tool_executed(mock_get_client, client, db):
    upload = _setup_upload(db)

    responses = [
        _mock_claude_response(
            text="Let me look that up.",
            tool_uses=[{
                "id": "tool_1",
                "name": "query_portfolio_summary",
                "input": {"upload_id": upload.id},
            }],
        ),
        _mock_claude_response("The portfolio has 1 property with 120k rent."),
    ]
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = responses
    mock_get_client.return_value = mock_client

    resp = client.post("/api/chat/message", json={"message": "How many properties?"})
    data = resp.json()
    assert "120k" in data["message"] or len(data["tool_results"]) > 0
    assert data["pending_confirmations"] == []


@patch("app.api.chat._get_client")
def test_chat_write_tool_needs_confirmation(mock_get_client, client, db):
    tm = TenantMaster(tenant_name_canonical="Old Name")
    db.add(tm)
    db.commit()
    db.refresh(tm)

    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_claude_response(
        text="I'll update the tenant name.",
        tool_uses=[{
            "id": "tool_write_1",
            "name": "update_tenant",
            "input": {"tenant_id": tm.id, "tenant_name_canonical": "New Name"},
        }],
    )
    mock_get_client.return_value = mock_client

    resp = client.post("/api/chat/message", json={"message": "Rename tenant to New Name"})
    data = resp.json()
    assert len(data["pending_confirmations"]) == 1
    assert data["pending_confirmations"][0]["tool_name"] == "update_tenant"
    assert data["pending_confirmations"][0]["tool_use_id"] == "tool_write_1"

    db.refresh(tm)
    assert tm.tenant_name_canonical == "Old Name"


@patch("app.api.chat._get_client")
def test_chat_confirmed_write_executes(mock_get_client, client, db):
    tm = TenantMaster(tenant_name_canonical="Old Name")
    db.add(tm)
    db.commit()
    db.refresh(tm)

    responses = [
        _mock_claude_response(
            text="Updating now.",
            tool_uses=[{
                "id": "tool_write_1",
                "name": "update_tenant",
                "input": {"tenant_id": tm.id, "tenant_name_canonical": "New Name"},
            }],
        ),
        _mock_claude_response("Done! Tenant updated to 'New Name'."),
    ]
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = responses
    mock_get_client.return_value = mock_client

    resp = client.post("/api/chat/message", json={
        "message": "Yes, please update",
        "confirmed_tool_calls": ["tool_write_1"],
    })
    data = resp.json()
    assert data["pending_confirmations"] == []

    db.refresh(tm)
    assert tm.tenant_name_canonical == "New Name"


@patch("app.api.chat._get_client")
def test_chat_session_continuity(mock_get_client, client, db):
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _mock_claude_response("First reply")
    mock_get_client.return_value = mock_client

    resp1 = client.post("/api/chat/message", json={"message": "Hello"})
    session_id = resp1.json()["session_id"]

    mock_client.messages.create.return_value = _mock_claude_response("Second reply")
    resp2 = client.post("/api/chat/message", json={
        "session_id": session_id,
        "message": "Follow-up",
    })
    assert resp2.json()["session_id"] == session_id

    msgs_resp = client.get(f"/api/chat/sessions/{session_id}/messages")
    assert msgs_resp.status_code == 200
    messages = msgs_resp.json()
    assert len(messages) >= 3


def test_session_list_and_delete(client, db):
    s = ChatSession(title="Test session")
    db.add(s)
    db.commit()
    db.refresh(s)

    resp = client.get("/api/chat/sessions")
    assert resp.status_code == 200
    assert any(sess["id"] == s.id for sess in resp.json())

    del_resp = client.delete(f"/api/chat/sessions/{s.id}")
    assert del_resp.status_code == 200

    resp2 = client.get("/api/chat/sessions")
    assert not any(sess["id"] == s.id for sess in resp2.json())


def test_session_not_found(client):
    resp = client.get("/api/chat/sessions/99999/messages")
    assert resp.status_code == 404


@patch("app.api.chat._get_client")
def test_chat_session_not_found(mock_get_client, client):
    mock_get_client.return_value = MagicMock()
    resp = client.post("/api/chat/message", json={
        "session_id": 99999,
        "message": "test",
    })
    assert resp.status_code == 404
