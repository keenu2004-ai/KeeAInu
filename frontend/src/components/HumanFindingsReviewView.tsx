import React, { useState, useEffect } from "react";
import {
  UserCheck,
  CheckCircle2,
  History
} from "lucide-react";
import {
  fetchCandidateFindings,
  createCandidateFinding,
  submitFindingReviewDecision,
  fetchFindingDecisionHistory
} from "../services/api";
import {
  CandidateFinding,
  FindingReviewState,
  FindingSeverity
} from "../types/platform";

export const HumanFindingsReviewView: React.FC = () => {
  const [findings, setFindings] = useState<CandidateFinding[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<CandidateFinding | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [stateFilter, setStateFilter] = useState<string>("ALL");

  // Review submission state
  const [targetState, setTargetState] = useState<FindingReviewState>("CONFIRMED_DEFECT");
  const [severity, setSeverity] = useState<FindingSeverity>("MAJOR");
  const [reviewerName, setReviewerName] = useState("Chief NDT Inspector");
  const [reviewerRationale, setReviewerRationale] = useState("Visual inspection confirms high-cycle fatigue surface crack across trailing edge blade airfoil.");
  const [diagnosis, setDiagnosis] = useState("Compressor stage 2 thermal-mechanical stress crack.");
  const [advisoryAction, setAdvisoryAction] = useState("Advisory: Schedule borescope reinspection within 50 operating hours. Engineering disposition required before flight clearance.");
  const [submitting, setSubmitting] = useState(false);

  // New Finding Seed state
  const [creatingSeed, setCreatingSeed] = useState(false);

  const loadFindings = async () => {
    try {
      const params: any = {};
      if (stateFilter !== "ALL") params.review_state = stateFilter;
      const data = await fetchCandidateFindings(params);
      setFindings(data);
      if (data.length > 0 && (!selectedFinding || !data.some(f => f.id === selectedFinding.id))) {
        setSelectedFinding(data[0]);
        loadHistory(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load candidate findings:", err);
    }
  };

  const loadHistory = async (findingId: string) => {
    try {
      const hist = await fetchFindingDecisionHistory(findingId);
      setHistory(hist);
    } catch (err) {
      console.error("Failed to load finding history:", err);
    }
  };

  useEffect(() => {
    loadFindings();
  }, [stateFilter]);

  const handleSelectFinding = (finding: CandidateFinding) => {
    setSelectedFinding(finding);
    loadHistory(finding.id);
  };

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFinding) return;

    try {
      setSubmitting(true);
      const updated = await submitFindingReviewDecision(selectedFinding.id, {
        review_state: targetState,
        severity: severity,
        reviewed_by: reviewerName,
        reviewer_rationale: reviewerRationale,
        engineering_diagnosis: diagnosis,
        advisory_recommendation: advisoryAction
      });
      setSelectedFinding(updated);
      await loadHistory(updated.id);
      await loadFindings();
      alert(`Review decision recorded: ${targetState}`);
    } catch (err: any) {
      alert(`Review submission failed: ${err.message || err}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCreateSampleFinding = async () => {
    try {
      setCreatingSeed(true);
      const newFinding = await createCandidateFinding({
        id: `fnd_obs_${Date.now()}`,
        asset_id: "ast_synthetic_demo_001",
        frame_index: 12,
        timestamp_ms: 400.0,
        timestamp_provenance: "NOMINAL_APPROXIMATE",
        equipment_family: "ENGINES_TURBINES",
        component_type: "COMPRESSOR_BLADE",
        candidate_defect: "CRACK",
        model_prediction_confidence: 0.89,
        is_simulated: true,
        review_state: "UNREVIEWED",
        severity: "UNSPECIFIED",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
      await loadFindings();
      setSelectedFinding(newFinding);
      loadHistory(newFinding.id);
    } catch (err: any) {
      alert(`Failed to create sample observation: ${err.message || err}`);
    } finally {
      setCreatingSeed(false);
    }
  };

  const getStateColor = (state: FindingReviewState) => {
    switch (state) {
      case "CONFIRMED_DEFECT": return "#ef4444";
      case "UNDER_REVIEW": return "#3b82f6";
      case "NO_VISIBLE_DEFECT": return "#10b981";
      case "UNCERTAIN_NEEDS_EXPERT": return "#f59e0b";
      case "REJECTED_FALSE_POSITIVE": return "#64748b";
      case "UNUSABLE_EVIDENCE": return "#6b7280";
      default: return "#94a3b8";
    }
  };

  return (
    <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "24px", overflowY: "auto", height: "100%" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #1f293d", paddingBottom: "16px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "700", color: "#f8fafc", margin: "0 0 6px 0", display: "flex", alignItems: "center", gap: "10px" }}>
            <UserCheck color="#38bdf8" /> Human Review Queue & Decision State Machine
          </h2>
          <p style={{ color: "#94a3b8", margin: 0, fontSize: "0.9rem" }}>
            All automated/simulated findings are candidate observations. Confirmation strictly requires qualified human inspector disposition and audit evidence.
          </p>
        </div>

        <button
          onClick={handleCreateSampleFinding}
          disabled={creatingSeed}
          style={{
            background: "#1e293b",
            border: "1px solid #334155",
            color: "#f8fafc",
            borderRadius: "6px",
            padding: "8px 14px",
            fontSize: "0.85rem",
            fontWeight: "600",
            cursor: "pointer"
          }}
        >
          + Seed Candidate Observation
        </button>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: "8px", background: "#111827", padding: "6px", borderRadius: "8px", border: "1px solid #1f293d" }}>
        {["ALL", "UNREVIEWED", "UNDER_REVIEW", "CONFIRMED_DEFECT", "NO_VISIBLE_DEFECT", "UNCERTAIN_NEEDS_EXPERT", "REJECTED_FALSE_POSITIVE"].map((s) => (
          <button
            key={s}
            onClick={() => setStateFilter(s)}
            style={{
              padding: "6px 12px",
              borderRadius: "6px",
              border: "none",
              background: stateFilter === s ? "#2563eb" : "transparent",
              color: stateFilter === s ? "#ffffff" : "#94a3b8",
              fontWeight: stateFilter === s ? "700" : "500",
              cursor: "pointer",
              fontSize: "0.8rem"
            }}
          >
            {s.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: "24px" }}>
        {/* Left: Candidate Findings List */}
        <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px", display: "flex", flexDirection: "column", gap: "12px", maxHeight: "650px", overflowY: "auto" }}>
          <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 6px 0" }}>
            Candidate Findings ({findings.length})
          </h3>

          {findings.length === 0 ? (
            <div style={{ color: "#64748b", fontSize: "0.85rem", textAlign: "center", padding: "30px 0" }}>
              No findings matching the filter. Click "Seed Candidate Observation" to create one.
            </div>
          ) : (
            findings.map((f) => (
              <div
                key={f.id}
                onClick={() => handleSelectFinding(f)}
                style={{
                  padding: "12px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  background: selectedFinding?.id === f.id ? "#1e293b" : "#070a13",
                  border: selectedFinding?.id === f.id ? "1px solid #38bdf8" : "1px solid #1f293d",
                  display: "flex",
                  flexDirection: "column",
                  gap: "6px"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: "700", color: "#f8fafc", fontSize: "0.85rem" }}>
                    {f.candidate_defect}
                  </span>
                  <span style={{
                    padding: "2px 6px",
                    borderRadius: "4px",
                    fontSize: "0.7rem",
                    fontWeight: "600",
                    background: `${getStateColor(f.review_state)}22`,
                    color: getStateColor(f.review_state),
                    border: `1px solid ${getStateColor(f.review_state)}`
                  }}>
                    {f.review_state}
                  </span>
                </div>

                <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                  {f.equipment_family} • {f.component_type}
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "#64748b" }}>
                  <span>Frame #{f.frame_index}</span>
                  {f.is_simulated && <span style={{ color: "#fbbf24" }}>[Simulated Baseline]</span>}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right: Selected Finding Inspector Workspace & Decision Submission */}
        {!selectedFinding ? (
          <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "40px", textAlign: "center", color: "#94a3b8" }}>
            Select a finding from the queue to conduct human review and disposition.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Finding Detail Card */}
            <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <div>
                  <h3 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#f8fafc", margin: "0 0 4px 0" }}>
                    {selectedFinding.candidate_defect} on {selectedFinding.component_type}
                  </h3>
                  <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    Asset: <strong style={{ color: "#cbd5e1" }}>{selectedFinding.asset_id}</strong> • Frame Index: {selectedFinding.frame_index}
                  </div>
                </div>

                <div style={{
                  padding: "6px 12px",
                  borderRadius: "6px",
                  fontSize: "0.85rem",
                  fontWeight: "700",
                  background: `${getStateColor(selectedFinding.review_state)}22`,
                  color: getStateColor(selectedFinding.review_state),
                  border: `1px solid ${getStateColor(selectedFinding.review_state)}`
                }}>
                  Status: {selectedFinding.review_state}
                </div>
              </div>

              {selectedFinding.is_simulated && (
                <div style={{ background: "#451a03", border: "1px solid #b45309", color: "#fef3c7", padding: "8px 12px", borderRadius: "6px", fontSize: "0.8rem", marginBottom: "14px" }}>
                  ⚠️ <strong>AI Transparency Notice:</strong> This candidate observation was generated by a deterministic test harness/simulation, NOT certified real-world inference.
                </div>
              )}

              {/* Inspector Disposition Form */}
              <form onSubmit={handleSubmitDecision} style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "12px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                  <div>
                    <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                      Target Review Disposition
                    </label>
                    <select
                      value={targetState}
                      onChange={(e) => setTargetState(e.target.value as FindingReviewState)}
                      style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                    >
                      <option value="CONFIRMED_DEFECT">CONFIRMED DEFECT (Requires Rationale)</option>
                      <option value="UNDER_REVIEW">UNDER REVIEW</option>
                      <option value="NO_VISIBLE_DEFECT">NO VISIBLE DEFECT</option>
                      <option value="UNCERTAIN_NEEDS_EXPERT">UNCERTAIN / NEEDS SENIOR EXPERT</option>
                      <option value="UNUSABLE_EVIDENCE">UNUSABLE EVIDENCE / BLURRED</option>
                      <option value="REJECTED_FALSE_POSITIVE">REJECTED FALSE POSITIVE</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                      Severity Assessment
                    </label>
                    <select
                      value={severity}
                      onChange={(e) => setSeverity(e.target.value as FindingSeverity)}
                      style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                    >
                      <option value="CRITICAL">CRITICAL (Immediate Grounding / Stop)</option>
                      <option value="MAJOR">MAJOR (Repair Required)</option>
                      <option value="MINOR">MINOR (Monitor & Track)</option>
                      <option value="INFORMATIONAL">INFORMATIONAL</option>
                      <option value="UNSPECIFIED">UNSPECIFIED</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                    Authorized Inspector Name
                  </label>
                  <input
                    type="text"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    required
                    style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                    Reviewer Rationale (Mandatory for Confirmation)
                  </label>
                  <textarea
                    rows={2}
                    value={reviewerRationale}
                    onChange={(e) => setReviewerRationale(e.target.value)}
                    required
                    style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                    Engineering Diagnosis
                  </label>
                  <input
                    type="text"
                    value={diagnosis}
                    onChange={(e) => setDiagnosis(e.target.value)}
                    style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                    Advisory Corrective Action Recommendation (Explicitly Subject to Qualified Engineering Review)
                  </label>
                  <textarea
                    rows={2}
                    value={advisoryAction}
                    onChange={(e) => setAdvisoryAction(e.target.value)}
                    style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  style={{
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
                  <CheckCircle2 size={16} /> Submit Verified Human Decision
                </button>
              </form>
            </div>

            {/* Decision History Audit Trail */}
            <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
              <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 14px 0", display: "flex", alignItems: "center", gap: "8px" }}>
                <History size={18} color="#38bdf8" /> Immutable State Transition Audit History ({history.length})
              </h3>

              {history.length === 0 ? (
                <div style={{ color: "#64748b", fontSize: "0.85rem" }}>
                  No historical state transitions recorded for this observation yet.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  {history.map((h) => (
                    <div
                      key={h.id}
                      style={{
                        padding: "10px 14px",
                        background: "#070a13",
                        border: "1px solid #1f293d",
                        borderRadius: "6px",
                        fontSize: "0.85rem"
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                        <div>
                          <span style={{ color: "#94a3b8" }}>{h.previous_state}</span> →{" "}
                          <strong style={{ color: "#38bdf8" }}>{h.new_state}</strong>
                        </div>
                        <span style={{ color: "#64748b", fontSize: "0.75rem" }}>
                          {new Date(h.transitioned_at).toLocaleString()}
                        </span>
                      </div>
                      <div style={{ color: "#cbd5e1", fontSize: "0.8rem" }}>
                        Inspector: <strong>{h.reviewed_by}</strong> ({h.severity})
                      </div>
                      <div style={{ color: "#94a3b8", fontSize: "0.8rem", marginTop: "4px", fontStyle: "italic" }}>
                        "{h.reviewer_rationale}"
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
