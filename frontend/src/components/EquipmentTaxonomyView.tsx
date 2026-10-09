import React, { useState, useEffect } from "react";
import {
  Tag,
  Search,
  CheckCircle2,
  Plus,
  ArrowRight,
  Layers,
  FileCheck
} from "lucide-react";
import {
  fetchTaxonomyStructure,
  translateSourceLabel,
  createDecoupledAnnotation,
  fetchDecoupledAnnotations
} from "../services/api";
import {
  EquipmentFamily,
  DecoupledAnnotation
} from "../types/platform";

export const EquipmentTaxonomyView: React.FC = () => {
  const [taxonomy, setTaxonomy] = useState<{
    equipment_families: string[];
    components_by_family: Record<string, string[]>;
    defects_by_family: Record<string, string[]>;
    all_defect_categories: string[];
  } | null>(null);

  const [annotations, setAnnotations] = useState<DecoupledAnnotation[]>([]);
  const [activeFamily, setActiveFamily] = useState<EquipmentFamily>("ENGINES_TURBINES");

  // Translation Sandbox states
  const [rawLabelInput, setRawLabelInput] = useState("compressor blade micro-crack");
  const [translationResult, setTranslationResult] = useState<any | null>(null);
  const [translating, setTranslating] = useState(false);

  // New Annotation creation state
  const [newAssetId, setNewAssetId] = useState("ast_synthetic_demo_001");
  const [newComponent, setNewComponent] = useState<string>("COMPRESSOR_BLADE");
  const [newDefect, setNewDefect] = useState<string>("CRACK");
  const [newCondition, setNewCondition] = useState("Longitudinal trailing edge stress crack");
  const [newAnnotator, setNewAnnotator] = useState("Lead NDT Inspector");
  const [creatingAnnot, setCreatingAnnot] = useState(false);

  const loadTaxonomy = async () => {
    try {
      const data = await fetchTaxonomyStructure();
      setTaxonomy(data);
      const annots = await fetchDecoupledAnnotations();
      setAnnotations(annots);
    } catch (err) {
      console.error("Failed to load taxonomy:", err);
    }
  };

  useEffect(() => {
    loadTaxonomy();
  }, []);

  const handleTranslate = async () => {
    try {
      setTranslating(true);
      const res = await translateSourceLabel(rawLabelInput, activeFamily);
      setTranslationResult(res);
    } catch (err) {
      alert(`Translation error: ${err}`);
    } finally {
      setTranslating(false);
    }
  };

  const handleCreateAnnotation = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setCreatingAnnot(true);
      await createDecoupledAnnotation({
        asset_id: newAssetId,
        equipment_family: activeFamily,
        component_type: newComponent,
        defect_category: newDefect,
        observed_visual_condition: newCondition,
        annotator_id: newAnnotator,
        source_raw_label: rawLabelInput
      });
      const refreshed = await fetchDecoupledAnnotations();
      setAnnotations(refreshed);
      alert("Decoupled annotation registered successfully with immutable evidence link.");
    } catch (err: any) {
      alert(`Annotation creation failed: ${err.message || err}`);
    } finally {
      setCreatingAnnot(false);
    }
  };

  const filteredComponents = taxonomy?.components_by_family[activeFamily] || [];
  const filteredDefects = taxonomy?.defects_by_family[activeFamily] || [];

  return (
    <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "24px", overflowY: "auto", height: "100%" }}>
      {/* Header Banner */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #1f293d", paddingBottom: "16px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "700", color: "#f8fafc", margin: "0 0 6px 0", display: "flex", alignItems: "center", gap: "10px" }}>
            <Tag color="#38bdf8" /> Equipment-Specific Taxonomy & Decoupled Labels
          </h2>
          <p style={{ color: "#94a3b8", margin: 0, fontSize: "0.9rem" }}>
            Enforce equipment-aware defect semantics across Engines/Turbines, Gearboxes/Transmissions, and Mechanical Assemblies without mutating third-party annotations.
          </p>
        </div>
      </div>

      {/* Equipment Family Switcher */}
      <div style={{ display: "flex", gap: "12px", background: "#111827", padding: "8px", borderRadius: "10px", border: "1px solid #1f293d" }}>
        {[
          { id: "ENGINES_TURBINES", label: "Engines & Turbines", icon: "✈️" },
          { id: "GEARBOXES_TRANSMISSIONS", label: "Gearboxes & Transmissions", icon: "⚙️" },
          { id: "OTHER_MECHANICAL_ASSEMBLIES", label: "Other Mechanical Assemblies", icon: "🏭" },
          { id: "UNKNOWN_EQUIPMENT", label: "Unknown / Unclassified", icon: "❓" }
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => {
              setActiveFamily(f.id as EquipmentFamily);
              if (taxonomy?.components_by_family[f.id]?.length) {
                setNewComponent(taxonomy.components_by_family[f.id][0]);
              }
            }}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: "8px",
              border: activeFamily === f.id ? "1px solid #38bdf8" : "1px solid transparent",
              background: activeFamily === f.id ? "#1e293b" : "transparent",
              color: activeFamily === f.id ? "#38bdf8" : "#94a3b8",
              fontWeight: activeFamily === f.id ? "700" : "500",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "8px",
              fontSize: "0.9rem"
            }}
          >
            <span>{f.icon}</span>
            <span>{f.label}</span>
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        {/* Left: Taxonomy Structure & Third-Party Label Translation Sandbox */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Active Family Components & Defects Catalog */}
          <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
            <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 14px 0", display: "flex", alignItems: "center", gap: "8px" }}>
              <Layers size={18} color="#38bdf8" /> Valid Context for {activeFamily.replace("_", " ")}
            </h3>
            <div style={{ marginBottom: "16px" }}>
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", color: "#94a3b8", fontWeight: "600", marginBottom: "8px" }}>
                Applicable Components ({filteredComponents.length})
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {filteredComponents.map((c) => (
                  <span key={c} style={{ background: "#1e293b", border: "1px solid #334155", color: "#cbd5e1", fontSize: "0.75rem", padding: "4px 8px", borderRadius: "4px" }}>
                    {c}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.8rem", textTransform: "uppercase", color: "#94a3b8", fontWeight: "600", marginBottom: "8px" }}>
                Applicable Defect Categories ({filteredDefects.length})
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {filteredDefects.map((d) => (
                  <span key={d} style={{ background: "#1e1b4b", border: "1px solid #4338ca", color: "#a5b4fc", fontSize: "0.75rem", padding: "4px 8px", borderRadius: "4px" }}>
                    {d}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Third-Party Source Label Translation Sandbox */}
          <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
            <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 8px 0", display: "flex", alignItems: "center", gap: "8px" }}>
              <Search size={18} color="#fbbf24" /> Third-Party Label Translation Sandbox
            </h3>
            <p style={{ color: "#94a3b8", fontSize: "0.85rem", margin: "0 0 14px 0" }}>
              Test deterministic mapping of third-party public dataset labels into standard KeeAInu defect categories with uncertainty tracking.
            </p>

            <div style={{ display: "flex", gap: "10px", marginBottom: "14px" }}>
              <input
                type="text"
                value={rawLabelInput}
                onChange={(e) => setRawLabelInput(e.target.value)}
                placeholder="e.g. pitting, spalling, burn_mark, crazing..."
                style={{
                  flex: 1,
                  background: "#070a13",
                  border: "1px solid #334155",
                  borderRadius: "6px",
                  padding: "8px 12px",
                  color: "#f8fafc",
                  fontSize: "0.85rem"
                }}
              />
              <button
                onClick={handleTranslate}
                disabled={translating}
                style={{
                  background: "#2563eb",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  fontWeight: "600",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px"
                }}
              >
                Translate <ArrowRight size={14} />
              </button>
            </div>

            {translationResult && (
              <div style={{ background: "#0b0f19", border: "1px solid #334155", borderRadius: "8px", padding: "12px", fontSize: "0.85rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ color: "#94a3b8" }}>Source Raw Label:</span>
                  <strong style={{ color: "#f8fafc" }}>{translationResult.source_raw_label}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ color: "#94a3b8" }}>Mapped Defect:</span>
                  <span style={{ color: "#38bdf8", fontWeight: "700" }}>{translationResult.mapped_defect_category}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ color: "#94a3b8" }}>Mapping Confidence:</span>
                  <span style={{
                    color: translationResult.mapping_confidence === "EXACT_MATCH" ? "#4ade80" : "#fbbf24",
                    fontWeight: "600"
                  }}>
                    {translationResult.mapping_confidence}
                  </span>
                </div>
                <div style={{ color: "#64748b", fontSize: "0.8rem", marginTop: "8px", borderTop: "1px solid #1e293b", paddingTop: "6px" }}>
                  {translationResult.rationale}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Decoupled Annotation Registration & Provenance Form */}
        <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
          <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 14px 0", display: "flex", alignItems: "center", gap: "8px" }}>
            <Plus size={18} color="#4ade80" /> Register Decoupled Equipment Annotation
          </h3>

          <form onSubmit={handleCreateAnnotation} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div>
              <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Target Asset ID</label>
              <input
                type="text"
                value={newAssetId}
                onChange={(e) => setNewAssetId(e.target.value)}
                required
                style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Component Type</label>
                <select
                  value={newComponent}
                  onChange={(e) => setNewComponent(e.target.value)}
                  style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                >
                  {filteredComponents.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Defect Category</label>
                <select
                  value={newDefect}
                  onChange={(e) => setNewDefect(e.target.value)}
                  style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                >
                  {filteredDefects.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Observed Visual Condition</label>
              <input
                type="text"
                value={newCondition}
                onChange={(e) => setNewCondition(e.target.value)}
                style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
              />
            </div>

            <div>
              <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Inspector / Annotator</label>
              <input
                type="text"
                value={newAnnotator}
                onChange={(e) => setNewAnnotator(e.target.value)}
                required
                style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
              />
            </div>

            <button
              type="submit"
              disabled={creatingAnnot}
              style={{
                marginTop: "10px",
                background: "#059669",
                color: "#ffffff",
                border: "none",
                borderRadius: "6px",
                padding: "10px 16px",
                fontWeight: "700",
                cursor: "pointer",
                fontSize: "0.9rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px"
              }}
            >
              <CheckCircle2 size={16} /> Save Traceable Annotation
            </button>
          </form>
        </div>
      </div>

      {/* Registered Annotations Table */}
      <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
        <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 14px 0", display: "flex", alignItems: "center", gap: "8px" }}>
          <FileCheck size={18} color="#38bdf8" /> Decoupled Traceable Annotations ({annotations.length})
        </h3>

        {annotations.length === 0 ? (
          <div style={{ textAlign: "center", padding: "30px", color: "#64748b", fontSize: "0.9rem" }}>
            No decoupled annotations registered yet. Register an equipment annotation above to populate ground truth.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1f293d", color: "#94a3b8", textAlign: "left" }}>
                <th style={{ padding: "8px" }}>ID</th>
                <th style={{ padding: "8px" }}>Asset ID</th>
                <th style={{ padding: "8px" }}>Equipment Family</th>
                <th style={{ padding: "8px" }}>Component</th>
                <th style={{ padding: "8px" }}>Defect</th>
                <th style={{ padding: "8px" }}>Confidence</th>
                <th style={{ padding: "8px" }}>Annotator</th>
                <th style={{ padding: "8px" }}>Created At</th>
              </tr>
            </thead>
            <tbody>
              {annotations.map((a) => (
                <tr key={a.id} style={{ borderBottom: "1px solid #161f36" }}>
                  <td style={{ padding: "8px", fontFamily: "monospace", color: "#38bdf8" }}>{a.id.slice(0, 10)}...</td>
                  <td style={{ padding: "8px", fontFamily: "monospace" }}>{a.asset_id}</td>
                  <td style={{ padding: "8px" }}>
                    <span style={{ background: "#1e293b", padding: "2px 6px", borderRadius: "4px", fontSize: "0.75rem" }}>
                      {a.equipment_family}
                    </span>
                  </td>
                  <td style={{ padding: "8px", color: "#cbd5e1" }}>{a.component_type}</td>
                  <td style={{ padding: "8px", color: "#fbbf24", fontWeight: "600" }}>{a.defect_category}</td>
                  <td style={{ padding: "8px", color: "#4ade80" }}>{a.mapping_confidence}</td>
                  <td style={{ padding: "8px", color: "#94a3b8" }}>{a.annotator_id}</td>
                  <td style={{ padding: "8px", color: "#64748b" }}>{new Date(a.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
