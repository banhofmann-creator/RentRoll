"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { ModuleRegistry, AllCommunityModule, type ColDef, type ColGroupDef, type CellValueChangedEvent } from "ag-grid-community";


import {
  type PropertyMaster,
  listProperties,
  updateProperty,
} from "@/lib/api";

ModuleRegistry.registerModules([AllCommunityModule]);

export default function PropertyGridPage() {
  const [rows, setRows] = useState<PropertyMaster[]>([]);
  const [loading, setLoading] = useState(true);
  const [saveStatus, setSaveStatus] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listProperties({ limit: 1000 });
      setRows(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onCellValueChanged = useCallback(
    async (event: CellValueChangedEvent<PropertyMaster>) => {
      const { data, colDef, newValue } = event;
      if (!data || !colDef.field) return;
      const field = colDef.field;
      setSaveStatus(`Saving ${field}...`);
      try {
        const val = newValue === "" ? null : newValue;
        await updateProperty(data.id, { [field]: val });
        setSaveStatus("Saved");
        setTimeout(() => setSaveStatus(""), 2000);
      } catch {
        setSaveStatus("Save failed");
        load();
      }
    },
    [load]
  );

  const columnDefs = useMemo<(ColDef | ColGroupDef)[]>(
    () => [
      {
        headerName: "ID",
        children: [
          { field: "property_id", headerName: "Property ID", pinned: "left", editable: false, width: 120 },
          { field: "city", headerName: "City", pinned: "left", editable: true, width: 140 },
        ],
      },
      {
        headerName: "Core / Location",
        children: [
          { field: "fund_csv_name", headerName: "Fund", editable: true, width: 120 },
          { field: "country", headerName: "Country", editable: true, width: 80 },
          { field: "region", headerName: "Region", editable: true, width: 100 },
          { field: "zip_code", headerName: "ZIP", editable: true, width: 80 },
          { field: "street", headerName: "Street", editable: true, width: 200 },
          { field: "location_quality", headerName: "Loc. Quality", editable: true, width: 100 },
          { field: "prop_state", headerName: "State", editable: true, width: 100 },
          { field: "ownership_type", headerName: "Ownership", editable: true, width: 100 },
          { field: "land_ownership", headerName: "Land Own.", editable: true, width: 100 },
        ],
      },
      {
        headerName: "Green Building",
        children: [
          { field: "green_building_vendor", headerName: "Vendor", editable: true, width: 100 },
          { field: "green_building_cert", headerName: "Cert", editable: true, width: 100 },
        ],
      },
      {
        headerName: "Financial / Valuation",
        children: [
          { field: "fair_value", headerName: "Fair Value", editable: true, width: 130, cellDataType: "number" },
          { field: "market_net_yield", headerName: "Net Yield", editable: true, width: 100, cellDataType: "number" },
          { field: "construction_year", headerName: "Built", editable: true, width: 80, cellDataType: "number" },
          { field: "plot_size_sqm", headerName: "Plot sqm", editable: true, width: 100, cellDataType: "number" },
          { field: "debt_property", headerName: "Debt", editable: true, width: 120, cellDataType: "number" },
          { field: "shareholder_loan", headerName: "SH Loan", editable: true, width: 120, cellDataType: "number" },
          { field: "risk_style", headerName: "Risk", editable: true, width: 80 },
        ],
      },
      {
        headerName: "ESG",
        children: [
          { field: "co2_emissions", headerName: "CO2", editable: true, width: 80, cellDataType: "number" },
          { field: "epc_rating", headerName: "EPC", editable: true, width: 70 },
          { field: "energy_intensity", headerName: "Energy Int.", editable: true, width: 100, cellDataType: "number" },
        ],
      },
      {
        headerName: "Technical",
        children: [
          { field: "tech_clear_height", headerName: "Clear H.", editable: true, width: 80, cellDataType: "number" },
          { field: "tech_loading_docks", headerName: "Docks", editable: true, width: 70, cellDataType: "number" },
          { field: "tech_sprinkler", headerName: "Sprinkler", editable: true, width: 90 },
        ],
      },
    ],
    []
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      sortable: true,
      filter: true,
      resizable: true,
    }),
    []
  );

  return (
    <div className="max-w-[100vw] mx-auto px-4 py-8">
      <nav className="text-sm text-garbe-blau-60 mb-4">
        <Link href="/master-data" className="hover:text-garbe-blau">
          Master Data
        </Link>
        {" > Properties > "}
        <span className="text-garbe-blau font-semibold">Grid Editor</span>
      </nav>

      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold text-garbe-blau">
          Property Grid Editor
        </h1>
        <div className="flex items-center gap-4">
          {saveStatus && (
            <span className="text-sm text-garbe-blau-60">{saveStatus}</span>
          )}
          <span className="text-sm text-garbe-blau-40">
            {rows.length} properties
          </span>
        </div>
      </div>

      <div
        className="ag-theme-quartz"
        style={{ height: "calc(100vh - 200px)", width: "100%" }}
      >
        {loading ? (
          <p className="text-garbe-blau-60 text-sm p-4">Loading...</p>
        ) : (
          <AgGridReact<PropertyMaster>
            rowData={rows}
            columnDefs={columnDefs}
            defaultColDef={defaultColDef}
            onCellValueChanged={onCellValueChanged}
            animateRows={false}
            getRowId={(params) => String(params.data.id)}
          />
        )}
      </div>
    </div>
  );
}
