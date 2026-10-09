import React from "react";
import { Plus, Folder, Calendar, User, Film, Tag } from "lucide-react";
import { InspectionSession } from "../types/inspection";

interface SessionListProps {
  sessions: InspectionSession[];
  onSelectSession: (session: InspectionSession) => void;
  onNewSession: () => void;
  loading: boolean;
}

export const SessionList: React.FC<SessionListProps> = ({
  sessions,
  onSelectSession,
  onNewSession,
  loading,
}) => {
  if (loading) {
    return (
      <div className="empty-state">
        <div style={{ fontSize: "1rem", color: "#06b6d4" }}>Loading inspection records...</div>
      </div>
    );
  }

  return (
    <div className="sessions-view">
      <div className="page-title-row">
        <div>
          <h2 style={{ fontSize: "1.35rem", fontWeight: "800", color: "#fff" }}>
            Inspection Sessions
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Select an active inspection to view footage, run defect analysis, and record review findings.
          </p>
        </div>
        <button className="btn btn-primary" onClick={onNewSession}>
          <Plus size={16} />
          New Inspection
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="empty-state" style={{ background: "var(--bg-card)", borderRadius: "16px", border: "1px dashed var(--border-subtle)", padding: "60px 20px" }}>
          <Folder size={48} color="#64748b" />
          <h3 style={{ color: "#fff", fontSize: "1.1rem" }}>No Inspection Sessions Found</h3>
          <p style={{ maxWidth: "400px", fontSize: "0.85rem" }}>
            Create your first inspection session to upload videoscope footage and analyze defect candidates.
          </p>
          <button className="btn btn-primary" onClick={onNewSession}>
            <Plus size={16} />
            Create Inspection Session
          </button>
        </div>
      ) : (
        <div className="session-grid">
          {sessions.map((session) => {
            const statusClass =
              session.status === "COMPLETED"
                ? "badge-completed"
                : session.status === "IN_REVIEW"
                ? "badge-in_review"
                : "badge-draft";

            const mediaCount = session.media?.length || 0;

            return (
              <div
                key={session.id}
                className="session-card"
                onClick={() => onSelectSession(session)}
              >
                <div className="session-card-header">
                  <h3 className="session-title">{session.title}</h3>
                  <span className={`badge ${statusClass}`}>{session.status}</span>
                </div>

                {session.asset_tag && (
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.8rem", color: "#06b6d4", fontFamily: "var(--font-mono)" }}>
                    <Tag size={13} />
                    <span>{session.asset_tag}</span>
                  </div>
                )}

                <div className="session-meta-row">
                  <div className="session-meta-item">
                    <User size={14} />
                    <span>{session.inspector_name}</span>
                  </div>
                  <div className="session-meta-item">
                    <Film size={14} />
                    <span>{mediaCount} file{mediaCount !== 1 ? "s" : ""}</span>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: "#64748b", marginTop: "auto", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                  <Calendar size={13} />
                  <span>{new Date(session.created_at).toLocaleString()}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
