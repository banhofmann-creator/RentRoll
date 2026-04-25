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


class InconsistencyListItem(BaseModel):
    id: int
    upload_id: int
    category: str
    severity: str
    entity_type: str | None
    entity_id: str | None
    field_name: str | None
    expected_value: str | None
    actual_value: str | None
    deviation_pct: float | None
    description: str
    status: str
    resolution_note: str | None
    resolved_by: str | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InconsistencyUpdate(BaseModel):
    status: str
    resolution_note: str | None = None
    resolved_by: str | None = None


class InconsistencySummary(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_category: dict[str, int]
    by_status: dict[str, int]
    has_blocking_errors: bool


# --- Fund Mapping ---

class FundMappingCreate(BaseModel):
    csv_fund_name: str
    bvi_fund_id: str | None = None
    description: str | None = None


class FundMappingUpdate(BaseModel):
    bvi_fund_id: str | None = None
    description: str | None = None


class FundMappingResponse(BaseModel):
    id: int
    csv_fund_name: str
    bvi_fund_id: str | None
    description: str | None

    model_config = {"from_attributes": True}


# --- Tenant ---

class TenantAliasCreate(BaseModel):
    csv_tenant_name: str
    property_id: str | None = None


class TenantAliasResponse(BaseModel):
    id: int
    tenant_master_id: int
    csv_tenant_name: str
    property_id: str | None

    model_config = {"from_attributes": True}


class TenantMasterCreate(BaseModel):
    tenant_name_canonical: str
    bvi_tenant_id: str | None = None
    nace_sector: str | None = None
    pd_min: float | None = None
    pd_max: float | None = None
    notes: str | None = None
    initial_alias: str | None = None


class TenantMasterUpdate(BaseModel):
    tenant_name_canonical: str | None = None
    bvi_tenant_id: str | None = None
    nace_sector: str | None = None
    pd_min: float | None = None
    pd_max: float | None = None
    notes: str | None = None


class TenantMasterResponse(BaseModel):
    id: int
    bvi_tenant_id: str | None
    tenant_name_canonical: str
    nace_sector: str | None
    pd_min: float | None
    pd_max: float | None
    notes: str | None
    aliases: list[TenantAliasResponse]

    model_config = {"from_attributes": True}


# --- Property Master ---

_PROPERTY_OPTIONAL_FIELDS = dict(
    fund_csv_name=(str | None, None),
    predecessor_id=(str | None, None),
    prop_state=(str | None, None),
    ownership_type=(str | None, None),
    land_ownership=(str | None, None),
    country=(str | None, None),
    region=(str | None, None),
    zip_code=(str | None, None),
    city=(str | None, None),
    street=(str | None, None),
    location_quality=(str | None, None),
    green_building_vendor=(str | None, None),
    green_building_cert=(str | None, None),
    green_building_from=(date | None, None),
    green_building_to=(date | None, None),
    ownership_share=(float | None, None),
    purchase_date=(date | None, None),
    construction_year=(int | None, None),
    risk_style=(str | None, None),
    fair_value=(float | None, None),
    market_net_yield=(float | None, None),
    last_valuation_date=(date | None, None),
    next_valuation_date=(date | None, None),
    plot_size_sqm=(float | None, None),
    debt_property=(float | None, None),
    shareholder_loan=(float | None, None),
    co2_emissions=(float | None, None),
    co2_measurement_year=(int | None, None),
    energy_intensity=(float | None, None),
    energy_intensity_normalised=(float | None, None),
    data_quality_energy=(str | None, None),
    energy_reference_area=(float | None, None),
    crrem_floor_areas_json=(dict | None, None),
    exposure_fossil_fuels=(float | None, None),
    exposure_energy_inefficiency=(float | None, None),
    waste_total=(float | None, None),
    waste_recycled_pct=(float | None, None),
    epc_rating=(str | None, None),
    tech_clear_height=(float | None, None),
    tech_floor_load_capacity=(float | None, None),
    tech_loading_docks=(int | None, None),
    tech_sprinkler=(str | None, None),
    tech_lighting=(str | None, None),
    tech_heating=(str | None, None),
    maintenance=(str | None, None),
)


class PropertyMasterCreate(BaseModel):
    property_id: str
    fund_csv_name: str | None = None
    predecessor_id: str | None = None
    prop_state: str | None = None
    ownership_type: str | None = None
    land_ownership: str | None = None
    country: str | None = None
    region: str | None = None
    zip_code: str | None = None
    city: str | None = None
    street: str | None = None
    location_quality: str | None = None
    green_building_vendor: str | None = None
    green_building_cert: str | None = None
    green_building_from: date | None = None
    green_building_to: date | None = None
    ownership_share: float | None = None
    purchase_date: date | None = None
    construction_year: int | None = None
    risk_style: str | None = None
    fair_value: float | None = None
    market_net_yield: float | None = None
    last_valuation_date: date | None = None
    next_valuation_date: date | None = None
    plot_size_sqm: float | None = None
    debt_property: float | None = None
    shareholder_loan: float | None = None
    co2_emissions: float | None = None
    co2_measurement_year: int | None = None
    energy_intensity: float | None = None
    energy_intensity_normalised: float | None = None
    data_quality_energy: str | None = None
    energy_reference_area: float | None = None
    crrem_floor_areas_json: dict | None = None
    exposure_fossil_fuels: float | None = None
    exposure_energy_inefficiency: float | None = None
    waste_total: float | None = None
    waste_recycled_pct: float | None = None
    epc_rating: str | None = None
    tech_clear_height: float | None = None
    tech_floor_load_capacity: float | None = None
    tech_loading_docks: int | None = None
    tech_sprinkler: str | None = None
    tech_lighting: str | None = None
    tech_heating: str | None = None
    maintenance: str | None = None


class PropertyMasterUpdate(BaseModel):
    fund_csv_name: str | None = None
    predecessor_id: str | None = None
    prop_state: str | None = None
    ownership_type: str | None = None
    land_ownership: str | None = None
    country: str | None = None
    region: str | None = None
    zip_code: str | None = None
    city: str | None = None
    street: str | None = None
    location_quality: str | None = None
    green_building_vendor: str | None = None
    green_building_cert: str | None = None
    green_building_from: date | None = None
    green_building_to: date | None = None
    ownership_share: float | None = None
    purchase_date: date | None = None
    construction_year: int | None = None
    risk_style: str | None = None
    fair_value: float | None = None
    market_net_yield: float | None = None
    last_valuation_date: date | None = None
    next_valuation_date: date | None = None
    plot_size_sqm: float | None = None
    debt_property: float | None = None
    shareholder_loan: float | None = None
    co2_emissions: float | None = None
    co2_measurement_year: int | None = None
    energy_intensity: float | None = None
    energy_intensity_normalised: float | None = None
    data_quality_energy: str | None = None
    energy_reference_area: float | None = None
    crrem_floor_areas_json: dict | None = None
    exposure_fossil_fuels: float | None = None
    exposure_energy_inefficiency: float | None = None
    waste_total: float | None = None
    waste_recycled_pct: float | None = None
    epc_rating: str | None = None
    tech_clear_height: float | None = None
    tech_floor_load_capacity: float | None = None
    tech_loading_docks: int | None = None
    tech_sprinkler: str | None = None
    tech_lighting: str | None = None
    tech_heating: str | None = None
    maintenance: str | None = None


class PropertyMasterResponse(BaseModel):
    id: int
    property_id: str
    fund_csv_name: str | None
    predecessor_id: str | None
    prop_state: str | None
    ownership_type: str | None
    land_ownership: str | None
    country: str | None
    region: str | None
    zip_code: str | None
    city: str | None
    street: str | None
    location_quality: str | None
    green_building_vendor: str | None
    green_building_cert: str | None
    green_building_from: date | None
    green_building_to: date | None
    ownership_share: float | None
    purchase_date: date | None
    construction_year: int | None
    risk_style: str | None
    fair_value: float | None
    market_net_yield: float | None
    last_valuation_date: date | None
    next_valuation_date: date | None
    plot_size_sqm: float | None
    debt_property: float | None
    shareholder_loan: float | None
    co2_emissions: float | None
    co2_measurement_year: int | None
    energy_intensity: float | None
    energy_intensity_normalised: float | None
    data_quality_energy: str | None
    energy_reference_area: float | None
    crrem_floor_areas_json: dict | None
    exposure_fossil_fuels: float | None
    exposure_energy_inefficiency: float | None
    waste_total: float | None
    waste_recycled_pct: float | None
    epc_rating: str | None
    tech_clear_height: float | None
    tech_floor_load_capacity: float | None
    tech_loading_docks: int | None
    tech_sprinkler: str | None
    tech_lighting: str | None
    tech_heating: str | None
    maintenance: str | None

    model_config = {"from_attributes": True}


# --- Unmapped Items ---

class UnmappedItem(BaseModel):
    entity_type: str
    entity_id: str
    upload_count: int
    inconsistency_ids: list[int]


# --- BVI Import ---

class BviImportPreview(BaseModel):
    properties_found: int
    new_properties: list[str]
    existing_properties: list[str]
    field_coverage: dict[str, int]
    bvi_fund_ids: list[str]
    warnings: list[str]


class BviImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    warnings: list[str]


# --- Completeness ---

class FieldStat(BaseModel):
    filled: int
    total: int
    fill_rate: float


class FieldGroupStats(BaseModel):
    fields: dict[str, FieldStat]


class CompletenessResponse(BaseModel):
    property_groups: dict[str, FieldGroupStats]
    tenant_fields: dict[str, FieldStat]


# --- Fuzzy Match ---

class FuzzyMatch(BaseModel):
    id: int
    name: str
    score: float


# --- Transform / Aggregation ---

class Z1RowResponse(BaseModel):
    bvi_fund_id: str | None
    stichtag: date | None
    currency: str
    bvi_tenant_id: str | None
    property_id: str | None
    tenant_name: str | None
    nace_sector: str | None
    pd_min: float | None
    pd_max: float | None
    contractual_rent: float


class G2RowResponse(BaseModel):
    fund_id: str | None
    stichtag: date | None
    currency: str
    property_id: str | None
    predecessor_id: str | None
    label: str | None
    prop_state: str | None
    ownership_type: str | None
    land_ownership: str | None
    country: str | None
    region: str | None
    zip_code: str | None
    city: str | None
    street: str | None
    location_quality: str | None
    green_building_vendor: str | None
    green_building_cert: str | None
    green_building_from: date | None
    green_building_to: date | None
    ownership_share: float | None
    purchase_date: date | None
    construction_year: int | None
    use_type_primary: str | None
    risk_style: str | None
    fair_value: float | None
    market_rental_value: float
    market_net_yield: float | None
    last_valuation_date: date | None
    next_valuation_date: date | None
    area_measure: str
    plot_size_sqm: float | None
    rentable_area: float
    tenant_count: int
    floorspace_let: float
    area_office: float
    area_mezzanine: float
    area_industrial: float
    area_outdoor: float
    area_gastronomy: float
    area_retail: float
    area_hotel: float
    area_ramp: float
    area_residential: float
    area_other: float
    parking_total: int
    parking_let: int
    debt_property: float | None
    shareholder_loan: float | None
    contractual_rent: float
    rent_per_sqm: float | None
    gross_potential_income: float
    rent_office: float
    rent_mezzanine: float
    rent_industrial_outdoor: float
    rent_industrial: float
    rent_outdoor: float
    rent_gastronomy: float
    rent_retail: float
    rent_hotel: float
    rent_ramp: float
    rent_residential: float
    rent_parking: float
    rent_other: float
    erv_total: float
    erv_office: float
    erv_mezzanine: float
    erv_industrial: float
    erv_outdoor: float
    erv_gastronomy: float
    erv_retail: float
    erv_hotel: float
    erv_ramp: float
    erv_residential: float
    erv_parking: float
    erv_other: float
    let_rent_office: float
    let_rent_mezzanine: float
    let_rent_industrial: float
    let_rent_outdoor: float
    let_rent_gastronomy: float
    let_rent_retail: float
    let_rent_hotel: float
    let_rent_ramp: float
    let_rent_residential: float
    let_rent_parking: float
    let_rent_other: float
    vacant_rent_office: float
    vacant_rent_mezzanine: float
    vacant_rent_industrial: float
    vacant_rent_outdoor: float
    vacant_rent_gastronomy: float
    vacant_rent_retail: float
    vacant_rent_hotel: float
    vacant_rent_ramp: float
    vacant_rent_residential: float
    vacant_rent_parking: float
    vacant_rent_other: float
    lease_expiry: dict
    lease_term_avg: float | None
    tenant_count_2: int
    co2_emissions: float | None
    co2_measurement_year: int | None
    energy_intensity: float | None
    energy_intensity_normalised: float | None
    data_quality_energy: str | None
    energy_reference_area: float | None
    crrem_floor_areas: dict | None
    exposure_fossil_fuels: float | None
    exposure_energy_inefficiency: float | None
    waste_total: float | None
    waste_recycled_pct: float | None
    epc_rating: str | None
    tech_clear_height: float | None
    tech_floor_load_capacity: float | None
    tech_loading_docks: int | None
    tech_sprinkler: str | None
    tech_lighting: str | None
    tech_heating: str | None
    maintenance: str | None
    reversion: float | None


class Z1PreviewResponse(BaseModel):
    rows: list[Z1RowResponse]
    total: int


class G2PreviewResponse(BaseModel):
    rows: list[G2RowResponse]
    total: int


class ValidationIssueResponse(BaseModel):
    property_id: str
    field: str
    expected: float
    actual: float
    deviation_pct: float


class ValidationResponse(BaseModel):
    issues: list[ValidationIssueResponse]
    total: int
    properties_checked: int
