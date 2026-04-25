"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  type PropertyMaster,
  getProperty,
  updateProperty,
} from "@/lib/api";

type FieldDef = {
  key: keyof PropertyMaster;
  label: string;
  type: "text" | "number" | "date" | "int";
};

const FIELD_GROUPS: { label: string; fields: FieldDef[] }[] = [
  {
    label: "Core / Location",
    fields: [
      { key: "property_id", label: "Property ID", type: "text" },
      { key: "fund_csv_name", label: "Fund", type: "text" },
      { key: "predecessor_id", label: "Predecessor ID", type: "text" },
      { key: "prop_state", label: "State", type: "text" },
      { key: "ownership_type", label: "Ownership Type", type: "text" },
      { key: "land_ownership", label: "Land Ownership", type: "text" },
      { key: "country", label: "Country", type: "text" },
      { key: "region", label: "Region", type: "text" },
      { key: "zip_code", label: "ZIP Code", type: "text" },
      { key: "city", label: "City", type: "text" },
      { key: "street", label: "Street", type: "text" },
      { key: "location_quality", label: "Location Quality", type: "text" },
    ],
  },
  {
    label: "Green Building",
    fields: [
      { key: "green_building_vendor", label: "Vendor", type: "text" },
      { key: "green_building_cert", label: "Certification", type: "text" },
      { key: "green_building_from", label: "Valid From", type: "date" },
      { key: "green_building_to", label: "Valid To", type: "date" },
    ],
  },
  {
    label: "Financial / Valuation",
    fields: [
      { key: "ownership_share", label: "Ownership Share", type: "number" },
      { key: "purchase_date", label: "Purchase Date", type: "date" },
      { key: "construction_year", label: "Construction Year", type: "int" },
      { key: "risk_style", label: "Risk Style", type: "text" },
      { key: "fair_value", label: "Fair Value", type: "number" },
      { key: "market_net_yield", label: "Market Net Yield", type: "number" },
      { key: "last_valuation_date", label: "Last Valuation", type: "date" },
      { key: "next_valuation_date", label: "Next Valuation", type: "date" },
      { key: "plot_size_sqm", label: "Plot Size (sqm)", type: "number" },
      { key: "debt_property", label: "Debt Property", type: "number" },
      { key: "shareholder_loan", label: "Shareholder Loan", type: "number" },
    ],
  },
  {
    label: "ESG / Sustainability",
    fields: [
      { key: "co2_emissions", label: "CO2 Emissions", type: "number" },
      { key: "co2_measurement_year", label: "CO2 Measurement Year", type: "int" },
      { key: "energy_intensity", label: "Energy Intensity", type: "number" },
      { key: "energy_intensity_normalised", label: "Energy Intensity (norm.)", type: "number" },
      { key: "data_quality_energy", label: "Data Quality Energy", type: "text" },
      { key: "energy_reference_area", label: "Energy Ref. Area", type: "number" },
      { key: "exposure_fossil_fuels", label: "Exposure Fossil Fuels", type: "number" },
      { key: "exposure_energy_inefficiency", label: "Exposure Energy Ineff.", type: "number" },
      { key: "waste_total", label: "Waste Total", type: "number" },
      { key: "waste_recycled_pct", label: "Waste Recycled %", type: "number" },
      { key: "epc_rating", label: "EPC Rating", type: "text" },
    ],
  },
  {
    label: "Technical Specs",
    fields: [
      { key: "tech_clear_height", label: "Clear Height (m)", type: "number" },
      { key: "tech_floor_load_capacity", label: "Floor Load (kN/sqm)", type: "number" },
      { key: "tech_loading_docks", label: "Loading Docks", type: "int" },
      { key: "tech_sprinkler", label: "Sprinkler", type: "text" },
      { key: "tech_lighting", label: "Lighting", type: "text" },
      { key: "tech_heating", label: "Heating", type: "text" },
      { key: "maintenance", label: "Maintenance", type: "text" },
    ],
  },
];

const CRREM_KEYS = [
  "office", "retail_high_street", "retail_shopping_centre",
  "retail_warehouse", "industrial_warehouse", "multi_family",
  "single_family", "hotel", "leisure", "health", "medical_office",
];

export default function PropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [property, setProperty] = useState<PropertyMaster | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [crrem, setCrrem] = useState<Record<string, string>>({});
  const [activeGroup, setActiveGroup] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!params?.id) return;
    getProperty(Number(params.id))
      .then((p) => {
        setProperty(p);
        const initial: Record<string, unknown> = {};
        for (const group of FIELD_GROUPS) {
          for (const f of group.fields) {
            initial[f.key] = p[f.key] ?? "";
          }
        }
        setForm(initial);
        const crremInit: Record<string, string> = {};
        for (const k of CRREM_KEYS) {
          crremInit[k] = String(p.crrem_floor_areas_json?.[k] ?? "");
        }
        setCrrem(crremInit);
      })
      .catch(() => setError("Property not found"));
  }, [params?.id]);

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <p className="text-garbe-rot">{error}</p>
      </div>
    );
  }
  if (!property) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <p className="text-garbe-blau-60 text-sm">Loading...</p>
      </div>
    );
  }

  const isDirty = () => {
    for (const group of FIELD_GROUPS) {
      for (const f of group.fields) {
        if (f.key === "property_id") continue;
        const orig = property[f.key] ?? "";
        const cur = form[f.key] ?? "";
        if (String(orig) !== String(cur)) return true;
      }
    }
    const origCrrem = property.crrem_floor_areas_json ?? {};
    for (const k of CRREM_KEYS) {
      if (String(origCrrem[k] ?? "") !== crrem[k]) return true;
    }
    return false;
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const changes: Record<string, unknown> = {};
      for (const group of FIELD_GROUPS) {
        for (const f of group.fields) {
          if (f.key === "property_id") continue;
          const orig = property[f.key] ?? "";
          const cur = form[f.key] ?? "";
          if (String(orig) !== String(cur)) {
            const val = cur === "" ? null : cur;
            if (f.type === "number" && val !== null) {
              changes[f.key] = Number(val);
            } else if (f.type === "int" && val !== null) {
              changes[f.key] = parseInt(String(val), 10);
            } else {
              changes[f.key] = val;
            }
          }
        }
      }
      const origCrrem = property.crrem_floor_areas_json ?? {};
      let crremChanged = false;
      for (const k of CRREM_KEYS) {
        if (String(origCrrem[k] ?? "") !== crrem[k]) {
          crremChanged = true;
          break;
        }
      }
      if (crremChanged) {
        const crremObj: Record<string, number> = {};
        for (const k of CRREM_KEYS) {
          if (crrem[k] !== "") crremObj[k] = Number(crrem[k]);
        }
        changes["crrem_floor_areas_json"] = Object.keys(crremObj).length > 0 ? crremObj : null;
      }

      if (Object.keys(changes).length > 0) {
        const updated = await updateProperty(property.id, changes);
        setProperty(updated);
        const initial: Record<string, unknown> = {};
        for (const group of FIELD_GROUPS) {
          for (const f of group.fields) {
            initial[f.key] = updated[f.key] ?? "";
          }
        }
        setForm(initial);
        const crremInit: Record<string, string> = {};
        for (const k of CRREM_KEYS) {
          crremInit[k] = String(updated.crrem_floor_areas_json?.[k] ?? "");
        }
        setCrrem(crremInit);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    const initial: Record<string, unknown> = {};
    for (const group of FIELD_GROUPS) {
      for (const f of group.fields) {
        initial[f.key] = property[f.key] ?? "";
      }
    }
    setForm(initial);
    const crremInit: Record<string, string> = {};
    for (const k of CRREM_KEYS) {
      crremInit[k] = String(property.crrem_floor_areas_json?.[k] ?? "");
    }
    setCrrem(crremInit);
  };

  const currentGroup = FIELD_GROUPS[activeGroup];
  const showCrrem = activeGroup === 3;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <nav className="text-sm text-garbe-blau-60 mb-4">
        <Link href="/master-data" className="hover:text-garbe-blau">
          Master Data
        </Link>
        {" > Properties > "}
        <span className="text-garbe-blau font-semibold">
          {property.property_id}
        </span>
      </nav>

      <h1 className="text-2xl font-semibold text-garbe-blau mb-6">
        Property {property.property_id}
        {property.city && (
          <span className="text-garbe-blau-60 font-normal">
            {" "}
            — {property.city}
          </span>
        )}
      </h1>

      <div className="flex gap-1 mb-6 flex-wrap">
        {FIELD_GROUPS.map((g, i) => (
          <button
            key={g.label}
            className={`px-3 py-1.5 text-xs font-semibold rounded-t-lg transition-colors ${
              activeGroup === i
                ? "bg-garbe-blau text-white"
                : "bg-garbe-blau-20/40 text-garbe-blau hover:bg-garbe-blau-20"
            }`}
            onClick={() => setActiveGroup(i)}
          >
            {g.label}
          </button>
        ))}
      </div>

      <div className="bg-white border border-garbe-neutral rounded-lg p-6 mb-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {currentGroup.fields.map((f) => (
            <div key={String(f.key)}>
              <label className="block text-xs font-semibold text-garbe-blau uppercase tracking-wider mb-1">
                {f.label}
              </label>
              <input
                className="form-input w-full"
                type={f.type === "date" ? "date" : f.type === "number" || f.type === "int" ? "number" : "text"}
                step={f.type === "number" ? "any" : undefined}
                value={String(form[f.key] ?? "")}
                disabled={f.key === "property_id"}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, [f.key]: e.target.value }))
                }
              />
            </div>
          ))}
        </div>

        {showCrrem && (
          <div className="mt-6">
            <h3 className="text-xs font-semibold text-garbe-blau uppercase tracking-wider mb-3">
              CRREM Floor Areas
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {CRREM_KEYS.map((k) => (
                <div key={k}>
                  <label className="block text-xs font-semibold text-garbe-blau-60 mb-1">
                    {k.replace(/_/g, " ")}
                  </label>
                  <input
                    className="form-input w-full"
                    type="number"
                    step="any"
                    value={crrem[k]}
                    onChange={(e) =>
                      setCrrem((prev) => ({ ...prev, [k]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-garbe-rot mb-4">{error}</p>}

      <div className="sticky bottom-0 bg-white border-t border-garbe-neutral py-3 flex gap-3 justify-end">
        <button
          className="px-4 py-2 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors"
          onClick={() => router.push("/master-data")}
        >
          Back
        </button>
        <button
          className="px-4 py-2 text-sm font-semibold border border-garbe-blau text-garbe-blau rounded-lg hover:bg-garbe-blau hover:text-white transition-colors disabled:opacity-40"
          onClick={handleCancel}
          disabled={!isDirty()}
        >
          Cancel
        </button>
        <button
          className="px-4 py-2 text-sm font-semibold bg-garbe-grun text-white rounded-lg hover:bg-garbe-grun-80 transition-colors disabled:opacity-40"
          onClick={handleSave}
          disabled={!isDirty() || saving}
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}
