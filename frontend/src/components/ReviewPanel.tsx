import React, { useState } from "react";
import { CheckCircle2, XCircle, Edit3, ShieldAlert, UserCheck, AlertTriangle } from "lucide-react";
import { Finding } from "../types/inspection";
import { submitReviewDecision } from "../services/api";

interface ReviewPanelProps {
  findings: Finding[];
  activeFindingId: string | null;
  onSelectFinding: (findingId: string) => void;
  onReviewSubmitted: (updatedFinding: Finding) => void;
  inspectorName: string;
}

export const ReviewPanel: React.FC<ReviewPanelProps> = ({
  findings,
  activeFindingId,
  onSelectFinding,
  onReviewSubmitted,
  inspectorName,
}) => {
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [selectedSeverity, setSelectedSeverity] = useState<Record<string, "CRITICAL" | "MAJOR" | "MINOR" | "INFORMATIONAL">>({});
  const [submitting, setSubmitting] = useState<string | null>(null);

  const handleDecision = async (
    findingId: string,
    status: "CONFIRMED" | "ADJUSTED" | "REJECTED"
  ) => {
    try {
      setSubmitting(findingId);
      const notes = reviewNotes[findingId] || "";
      const severity = selectedSeverity[findingId] || "INFORMATIONAL";

      const updated = await submitReviewDecision({
        finding_id: findingId,
        decision_status: status,
        severity: severity,
        reviewed_by: inspectorName || "Lead Inspector",
        inspector_notes: notes.trim() || undefined,
      });

      onReviewSubmitted(updated);
    } catch (err: any) {
      alert(`Review submission failed: ${err.message}`);
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="review-panel">
      <div className="panel-header">
        <div>
          <h3 style={{ fontSize: "1rem", fontWeight: "700" }}>Inspector Review Log</h3>
          <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
            {findings.length} Finding{findings.length !== 1 ? "s" : ""} Recorded
          </span>
        </div>
        <UserCheck size={18} color="#06b6d4" />
      </div>

      <div className="findings-list">
        {findings.length === 0 ? (
          <div className="empty-state">
            <ShieldAlert size={32} color="#64748b" />
            <p style={{ fontSize: "0.85rem" }}>No candidate defects detected yet.</p>
            <span style={{ fontSize: "0.75rem" }}>
              Run AI Defect Analysis on a selected frame to generate candidates.
            </span>
          </div>
        ) : (
          findings.map((finding) => {
            const isActive = finding.id === activeFindingId;
            const status = finding.decision_status || "PENDING_REVIEW";
            const severity = finding.severity || "INFORMATIONAL";

            return (
              <div
                key={finding.id}
                className={`finding-card ${isActive ? "active" : ""}`}
                onClick={() => onSelectFinding(finding.id)}
              >
                <div className="finding-card-header">
                  <span className="finding-class">{finding.defect_class}</span>
                  <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                    {finding.is_simulated && (
                      <span className="badge badge-simulated" title="Simulated prediction">
                        SIMULATED
                      </span>
                    )}
                    <span
                      className={`badge ${
                        status === "CONFIRMED"
                          ? "badge-completed"
                          : status === "REJECTED"
                          ? "btn-danger"
                          : "badge-in_review"
                      }`}
                    >
                      {status}
                    </span>
                  </div>
                </div>

                <div className="finding-info-row">
                  <span>Frame: {finding.frame_index}</span>
                  <span>Confidence: {(finding.confidence_score * 100).toFixed(0)}%</span>
                  <span>TS: {(finding.timestamp_ms / 1000).toFixed(2)}s</span>
                </div>

                {finding.is_simulated && (
                  <div className="simulated-banner">
                    <AlertTriangle size={14} color="#f59e0b" />
                    <span>Simulated anomaly — requires qualified sign-off.</span>
                  </div>
                )}

                {/* Review Controls */}
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "4px" }}>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <label style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Severity:</label>
                    <select
                      className="form-select"
                      style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                      value={selectedSeverity[finding.id] || severity}
                      onChange={(e) =>
                        setSelectedSeverity({
                          ...selectedSeverity,
                          [finding.id]: e.target.value as any,
                        })
                      }
                    >
                      <option value="CRITICAL">Critical</option>
                      <option value="MAJOR">Major</option>
                      <option value="MINOR">Minor</option>
                      <option value="INFORMATIONAL">Informational</option>
                    </select>
                  </div>

                  <input
                    type="text"
                    className="form-input"
                    style={{ padding: "6px 10px", fontSize: "0.75rem" }}
                    placeholder="Inspector notes..."
                    value={
                      reviewNotes[finding.id] !== undefined
                        ? reviewNotes[finding.id]
                        : finding.inspector_notes || ""
                    }
                    onChange={(e) =>
                      setReviewNotes({
                        ...reviewNotes,
                        [finding.id]: e.target.value,
                      })
                    }
                  />

                  <div className="review-action-row">
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1, borderColor: "#10b981", color: "#10b981" }}
                      disabled={submitting === finding.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDecision(finding.id, "CONFIRMED");
                      }}
                    >
                      <CheckCircle2 size={13} />
                      Confirm
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1, borderColor: "#3b82f6", color: "#60a5fa" }}
                      disabled={submitting === finding.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDecision(finding.id, "ADJUSTED");
                      }}
                    >
                      <Edit3 size={13} />
                      Adjust
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      style={{ flex: 1 }}
                      disabled={submitting === finding.id}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDecision(finding.id, "REJECTED");
                      }}
                    >
                      <XCircle size={13} />
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
