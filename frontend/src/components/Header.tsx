import React from "react";
import { Eye, Plus, RefreshCw, Layers, Database } from "lucide-react";

interface HeaderProps {
  onNewSession: () => void;
  onRefresh: () => void;
  onBackToSessions?: () => void;
  activeSessionTitle?: string;
  activeTab: "INSPECTIONS" | "DISCOVERY";
  onTabChange: (tab: "INSPECTIONS" | "DISCOVERY") => void;
}

export const Header: React.FC<HeaderProps> = ({
  onNewSession,
  onRefresh,
  onBackToSessions,
  activeSessionTitle,
  activeTab,
  onTabChange,
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
            <span className="logo-tag">NDT INTELLIGENCE</span>
          </div>
          {activeSessionTitle && (
            <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
              Session: <strong style={{ color: "#f8fafc" }}>{activeSessionTitle}</strong>
            </span>
          )}
        </div>
      </div>

      {/* Center Navigation Tabs */}
      <div style={{ display: "flex", gap: "6px", background: "var(--bg-dark)", padding: "4px", borderRadius: "8px", border: "1px solid var(--border-subtle)" }}>
        <button
          className="btn btn-sm"
          style={{
            background: activeTab === "INSPECTIONS" ? "var(--accent-primary)" : "transparent",
            color: activeTab === "INSPECTIONS" ? "#070a13" : "#94a3b8",
            fontWeight: activeTab === "INSPECTIONS" ? "700" : "500",
            display: "flex",
            alignItems: "center",
            gap: "6px"
          }}
          onClick={() => onTabChange("INSPECTIONS")}
        >
          <Layers size={14} />
          Inspection Sessions
        </button>

        <button
          className="btn btn-sm"
          style={{
            background: activeTab === "DISCOVERY" ? "var(--accent-primary)" : "transparent",
            color: activeTab === "DISCOVERY" ? "#070a13" : "#94a3b8",
            fontWeight: activeTab === "DISCOVERY" ? "700" : "500",
            display: "flex",
            alignItems: "center",
            gap: "6px"
          }}
          onClick={() => onTabChange("DISCOVERY")}
        >
          <Database size={14} />
          Dataset Discovery & Profiling
        </button>
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

