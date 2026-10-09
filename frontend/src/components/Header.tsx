import React from "react";
import { Eye, Plus, RefreshCw } from "lucide-react";

interface HeaderProps {
  onNewSession: () => void;
  onRefresh: () => void;
  onBackToSessions?: () => void;
  activeSessionTitle?: string;
}

export const Header: React.FC<HeaderProps> = ({
  onNewSession,
  onRefresh,
  onBackToSessions,
  activeSessionTitle,
}) => {
  return (
    <header className="header">
      <div className="logo-area">
        <div className="logo-badge">
          <Eye size={20} color="#070a13" />
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span className="logo-text">KeeAInu</span>
            <span className="logo-tag">NDT WORKSPACE</span>
          </div>
          {activeSessionTitle && (
            <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
              Session: <strong style={{ color: "#f8fafc" }}>{activeSessionTitle}</strong>
            </span>
          )}
        </div>
      </div>

      <div className="header-actions">
        {activeSessionTitle && (
          <button className="btn btn-secondary btn-sm" onClick={onBackToSessions}>
            All Sessions
          </button>
        )}
        <button className="btn btn-secondary btn-sm" onClick={onRefresh} title="Refresh Data">
          <RefreshCw size={14} />
          Refresh
        </button>
        <button className="btn btn-primary btn-sm" onClick={onNewSession}>
          <Plus size={14} />
          New Inspection
        </button>
      </div>
    </header>
  );
};
