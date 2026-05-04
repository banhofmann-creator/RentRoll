from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CsvUpload(Base):
    __tablename__ = "csv_uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(500))
    upload_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    stichtag: Mapped[date | None] = mapped_column(Date)
    fund_label: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="processing")
    row_count: Mapped[int | None] = mapped_column(Integer)
    data_row_count: Mapped[int | None] = mapped_column(Integer)
    summary_row_count: Mapped[int | None] = mapped_column(Integer)
    orphan_row_count: Mapped[int | None] = mapped_column(Integer)
    column_fingerprint: Mapped[str | None] = mapped_column(String(64))
    column_headers_json: Mapped[dict | None] = mapped_column(JSON)
    parser_warnings_json: Mapped[list | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)

    rows = relationship("RawRentRoll", back_populates="upload", cascade="all, delete-orphan")
    inconsistencies = relationship("DataInconsistency", back_populates="upload", cascade="all, delete-orphan")


class RawRentRoll(Base):
    __tablename__ = "raw_rent_roll"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("csv_uploads.id", ondelete="CASCADE"))
    row_number: Mapped[int] = mapped_column(Integer)
    row_type: Mapped[str] = mapped_column(String(20))  # data, property_summary, orphan, total

    fund: Mapped[str | None] = mapped_column(String(500))
    fund_inherited: Mapped[bool] = mapped_column(Boolean, default=False)
    property_id: Mapped[str | None] = mapped_column(String(50))
    property_name: Mapped[str | None] = mapped_column(String(500))
    garbe_office: Mapped[str | None] = mapped_column(String(200))

    unit_id: Mapped[str | None] = mapped_column(String(50))
    unit_type: Mapped[str | None] = mapped_column(String(100))
    floor: Mapped[str | None] = mapped_column(String(50))
    parking_count: Mapped[int | None] = mapped_column(Integer)
    area_sqm: Mapped[float | None] = mapped_column(Numeric(14, 4))

    lease_id: Mapped[str | None] = mapped_column(String(50))
    tenant_name: Mapped[str | None] = mapped_column(String(500))
    lease_start: Mapped[date | None] = mapped_column(Date)
    lease_end_agreed: Mapped[date | None] = mapped_column(Date)
    lease_end_termination: Mapped[date | None] = mapped_column(Date)
    lease_end_actual: Mapped[date | None] = mapped_column(Date)
    special_termination_notice: Mapped[str | None] = mapped_column(String(100))
    special_termination_date: Mapped[date | None] = mapped_column(Date)
    notice_period: Mapped[str | None] = mapped_column(String(100))
    notice_date: Mapped[date | None] = mapped_column(Date)
    option_duration_months: Mapped[int | None] = mapped_column(Integer)
    option_exercise_deadline: Mapped[date | None] = mapped_column(Date)
    lease_end_after_option: Mapped[date | None] = mapped_column(Date)
    additional_options: Mapped[int | None] = mapped_column(Integer)
    max_lease_term: Mapped[str | None] = mapped_column(String(100))
    wault: Mapped[float | None] = mapped_column(Numeric(10, 4))
    waulb: Mapped[float | None] = mapped_column(Numeric(10, 4))
    waule: Mapped[float | None] = mapped_column(Numeric(10, 4))

    annual_net_rent: Mapped[float | None] = mapped_column(Numeric(14, 2))
    monthly_net_rent: Mapped[float | None] = mapped_column(Numeric(14, 2))
    investment_rent: Mapped[float | None] = mapped_column(Numeric(14, 2))
    rent_free_end: Mapped[date | None] = mapped_column(Date)
    rent_free_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    market_rent_monthly: Mapped[float | None] = mapped_column(Numeric(14, 2))
    erv_monthly: Mapped[float | None] = mapped_column(Numeric(14, 2))
    reversion_potential_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    net_rent_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    market_rent_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    erv_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))

    service_charge_advance: Mapped[float | None] = mapped_column(Numeric(14, 2))
    service_charge_lumpsum: Mapped[float | None] = mapped_column(Numeric(14, 2))
    sc_advance_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    sc_lumpsum_per_sqm_pa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    total_gross_rent_monthly: Mapped[float | None] = mapped_column(Numeric(14, 2))
    total_gross_rent_per_sqm: Mapped[float | None] = mapped_column(Numeric(14, 4))
    vat_liable: Mapped[str | None] = mapped_column(String(20))

    pct_rent_increase: Mapped[str | None] = mapped_column(String(10))
    increase_percentage: Mapped[float | None] = mapped_column(Numeric(10, 4))
    next_increase_date: Mapped[date | None] = mapped_column(Date)
    escalation_cycles: Mapped[str | None] = mapped_column(String(200))

    index_escalation: Mapped[str | None] = mapped_column(String(10))
    index_type: Mapped[str | None] = mapped_column(String(100))
    threshold: Mapped[str | None] = mapped_column(String(100))
    index_ref_date: Mapped[date | None] = mapped_column(Date)
    passthrough_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    green_lease: Mapped[int | None] = mapped_column(Integer)

    upload = relationship("CsvUpload", back_populates="rows")


class FundMapping(Base):
    __tablename__ = "fund_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    csv_fund_name: Mapped[str] = mapped_column(String(100), unique=True)
    bvi_fund_id: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)


class TenantMaster(Base):
    __tablename__ = "tenant_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    bvi_tenant_id: Mapped[str | None] = mapped_column(String(50), unique=True)
    tenant_name_canonical: Mapped[str] = mapped_column(String(500))
    nace_sector: Mapped[str | None] = mapped_column(String(100))
    pd_min: Mapped[float | None] = mapped_column(Numeric(10, 6))
    pd_max: Mapped[float | None] = mapped_column(Numeric(10, 6))
    notes: Mapped[str | None] = mapped_column(Text)

    aliases = relationship("TenantNameAlias", back_populates="tenant_master", cascade="all, delete-orphan")


class TenantNameAlias(Base):
    __tablename__ = "tenant_name_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_master_id: Mapped[int] = mapped_column(ForeignKey("tenant_master.id", ondelete="CASCADE"))
    csv_tenant_name: Mapped[str] = mapped_column(String(500))
    property_id: Mapped[str | None] = mapped_column(String(20))

    tenant_master = relationship("TenantMaster", back_populates="aliases")


class PropertyMaster(Base):
    __tablename__ = "property_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[str] = mapped_column(String(20), unique=True)
    fund_csv_name: Mapped[str | None] = mapped_column(String(100))
    predecessor_id: Mapped[str | None] = mapped_column(String(100))
    prop_state: Mapped[str | None] = mapped_column(String(50))
    ownership_type: Mapped[str | None] = mapped_column(String(50))
    land_ownership: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(10))
    region: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(200))
    street: Mapped[str | None] = mapped_column(String(500))
    location_quality: Mapped[str | None] = mapped_column(String(10))

    green_building_vendor: Mapped[str | None] = mapped_column(String(50))
    green_building_cert: Mapped[str | None] = mapped_column(String(50))
    green_building_from: Mapped[date | None] = mapped_column(Date)
    green_building_to: Mapped[date | None] = mapped_column(Date)

    ownership_share: Mapped[float | None] = mapped_column(Numeric(5, 4))
    purchase_date: Mapped[date | None] = mapped_column(Date)
    construction_year: Mapped[int | None] = mapped_column(Integer)
    risk_style: Mapped[str | None] = mapped_column(String(50))
    fair_value: Mapped[float | None] = mapped_column(Numeric(16, 2))
    market_net_yield: Mapped[float | None] = mapped_column(Numeric(10, 6))
    last_valuation_date: Mapped[date | None] = mapped_column(Date)
    next_valuation_date: Mapped[date | None] = mapped_column(Date)
    plot_size_sqm: Mapped[float | None] = mapped_column(Numeric(14, 2))
    debt_property: Mapped[float | None] = mapped_column(Numeric(16, 2))
    shareholder_loan: Mapped[float | None] = mapped_column(Numeric(16, 2))

    # ESG / Sustainability
    co2_emissions: Mapped[float | None] = mapped_column(Numeric(10, 2))
    co2_measurement_year: Mapped[int | None] = mapped_column(Integer)
    energy_intensity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    energy_intensity_normalised: Mapped[float | None] = mapped_column(Numeric(10, 2))
    data_quality_energy: Mapped[str | None] = mapped_column(String(50))
    energy_reference_area: Mapped[float | None] = mapped_column(Numeric(14, 2))
    crrem_floor_areas_json: Mapped[dict | None] = mapped_column(JSON)
    exposure_fossil_fuels: Mapped[float | None] = mapped_column(Numeric(10, 4))
    exposure_energy_inefficiency: Mapped[float | None] = mapped_column(Numeric(10, 4))
    waste_total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    waste_recycled_pct: Mapped[float | None] = mapped_column(Numeric(5, 4))
    epc_rating: Mapped[str | None] = mapped_column(String(10))

    # Technical Specifications
    tech_clear_height: Mapped[float | None] = mapped_column(Numeric(6, 2))
    tech_floor_load_capacity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    tech_loading_docks: Mapped[int | None] = mapped_column(Integer)
    tech_sprinkler: Mapped[str | None] = mapped_column(String(100))
    tech_lighting: Mapped[str | None] = mapped_column(String(100))
    tech_heating: Mapped[str | None] = mapped_column(String(100))
    maintenance: Mapped[str | None] = mapped_column(String(200))


class DataInconsistency(Base):
    __tablename__ = "data_inconsistencies"

    id: Mapped[int] = mapped_column(primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("csv_uploads.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    field_name: Mapped[str | None] = mapped_column(String(100))
    expected_value: Mapped[str | None] = mapped_column(Text)
    actual_value: Mapped[str | None] = mapped_column(Text)
    deviation_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    resolution_note: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(String(100))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    upload = relationship("CsvUpload", back_populates="inconsistencies")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    tool_calls_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


class MasterDataAudit(Base):
    __tablename__ = "master_data_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(50))
    record_id: Mapped[int] = mapped_column(Integer)
    field_name: Mapped[str] = mapped_column(String(100))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    change_source: Mapped[str] = mapped_column(String(50))
    changed_by: Mapped[str | None] = mapped_column(String(100))
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    session_id: Mapped[int | None] = mapped_column(Integer)


class ReportingPeriod(Base):
    __tablename__ = "reporting_periods"

    id: Mapped[int] = mapped_column(primary_key=True)
    stichtag: Mapped[date] = mapped_column(Date, unique=True)
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("csv_uploads.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    finalized_by: Mapped[str | None] = mapped_column(String(100))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SnapshotPropertyMaster(Base):
    __tablename__ = "snapshot_property_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="CASCADE"))
    property_id: Mapped[str] = mapped_column(String(20))
    fund_csv_name: Mapped[str | None] = mapped_column(String(100))
    predecessor_id: Mapped[str | None] = mapped_column(String(100))
    prop_state: Mapped[str | None] = mapped_column(String(50))
    ownership_type: Mapped[str | None] = mapped_column(String(50))
    land_ownership: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(10))
    region: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(20))
    city: Mapped[str | None] = mapped_column(String(200))
    street: Mapped[str | None] = mapped_column(String(500))
    location_quality: Mapped[str | None] = mapped_column(String(10))
    green_building_vendor: Mapped[str | None] = mapped_column(String(50))
    green_building_cert: Mapped[str | None] = mapped_column(String(50))
    green_building_from: Mapped[date | None] = mapped_column(Date)
    green_building_to: Mapped[date | None] = mapped_column(Date)
    ownership_share: Mapped[float | None] = mapped_column(Numeric(5, 4))
    purchase_date: Mapped[date | None] = mapped_column(Date)
    construction_year: Mapped[int | None] = mapped_column(Integer)
    risk_style: Mapped[str | None] = mapped_column(String(50))
    fair_value: Mapped[float | None] = mapped_column(Numeric(16, 2))
    market_net_yield: Mapped[float | None] = mapped_column(Numeric(10, 6))
    last_valuation_date: Mapped[date | None] = mapped_column(Date)
    next_valuation_date: Mapped[date | None] = mapped_column(Date)
    plot_size_sqm: Mapped[float | None] = mapped_column(Numeric(14, 2))
    debt_property: Mapped[float | None] = mapped_column(Numeric(16, 2))
    shareholder_loan: Mapped[float | None] = mapped_column(Numeric(16, 2))
    co2_emissions: Mapped[float | None] = mapped_column(Numeric(10, 2))
    co2_measurement_year: Mapped[int | None] = mapped_column(Integer)
    energy_intensity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    energy_intensity_normalised: Mapped[float | None] = mapped_column(Numeric(10, 2))
    data_quality_energy: Mapped[str | None] = mapped_column(String(50))
    energy_reference_area: Mapped[float | None] = mapped_column(Numeric(14, 2))
    crrem_floor_areas_json: Mapped[dict | None] = mapped_column(JSON)
    exposure_fossil_fuels: Mapped[float | None] = mapped_column(Numeric(10, 4))
    exposure_energy_inefficiency: Mapped[float | None] = mapped_column(Numeric(10, 4))
    waste_total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    waste_recycled_pct: Mapped[float | None] = mapped_column(Numeric(5, 4))
    epc_rating: Mapped[str | None] = mapped_column(String(10))
    tech_clear_height: Mapped[float | None] = mapped_column(Numeric(6, 2))
    tech_floor_load_capacity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    tech_loading_docks: Mapped[int | None] = mapped_column(Integer)
    tech_sprinkler: Mapped[str | None] = mapped_column(String(100))
    tech_lighting: Mapped[str | None] = mapped_column(String(100))
    tech_heating: Mapped[str | None] = mapped_column(String(100))
    maintenance: Mapped[str | None] = mapped_column(String(200))


class SnapshotTenantMaster(Base):
    __tablename__ = "snapshot_tenant_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="CASCADE"))
    bvi_tenant_id: Mapped[str | None] = mapped_column(String(50))
    tenant_name_canonical: Mapped[str] = mapped_column(String(500))
    nace_sector: Mapped[str | None] = mapped_column(String(100))
    pd_min: Mapped[float | None] = mapped_column(Numeric(10, 6))
    pd_max: Mapped[float | None] = mapped_column(Numeric(10, 6))
    notes: Mapped[str | None] = mapped_column(Text)


class SnapshotTenantNameAlias(Base):
    __tablename__ = "snapshot_tenant_name_alias"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="CASCADE"))
    snapshot_tenant_master_id: Mapped[int] = mapped_column(
        ForeignKey("snapshot_tenant_master.id", ondelete="CASCADE")
    )
    csv_tenant_name: Mapped[str] = mapped_column(String(500))
    property_id: Mapped[str | None] = mapped_column(String(20))


class SnapshotFundMapping(Base):
    __tablename__ = "snapshot_fund_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    reporting_period_id: Mapped[int] = mapped_column(ForeignKey("reporting_periods.id", ondelete="CASCADE"))
    csv_fund_name: Mapped[str] = mapped_column(String(100))
    bvi_fund_id: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
