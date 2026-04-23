from datetime import date, datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    message: str


class UploadDetail(BaseModel):
    id: int
    filename: str
    upload_date: datetime
    stichtag: date | None
    fund_label: str | None
    status: str
    row_count: int | None
    data_row_count: int | None
    summary_row_count: int | None
    orphan_row_count: int | None
    column_fingerprint: str | None
    parser_warnings_json: list | None
    error_message: str | None

    model_config = {"from_attributes": True}


class UploadListItem(BaseModel):
    id: int
    filename: str
    upload_date: datetime
    stichtag: date | None
    status: str
    row_count: int | None

    model_config = {"from_attributes": True}


class RawRentRollRow(BaseModel):
    id: int
    row_number: int
    row_type: str
    fund: str | None
    fund_inherited: bool
    property_id: str | None
    property_name: str | None
    unit_id: str | None
    unit_type: str | None
    tenant_name: str | None
    area_sqm: float | None
    annual_net_rent: float | None
    monthly_net_rent: float | None
    market_rent_monthly: float | None
    lease_start: date | None
    lease_end_actual: date | None

    model_config = {"from_attributes": True}


class ParseStats(BaseModel):
    total_rows: int
    data_rows: int
    summary_rows: int
    orphan_rows: int
    total_rows_found: int
    funds: list[str]
    properties: int
    warnings: list[str]
