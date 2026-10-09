import React, { useState } from "react";
import { X, Check } from "lucide-react";
import { createSession } from "../services/api";
import { InspectionSession } from "../types/inspection";

interface CreateSessionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSessionCreated: (session: InspectionSession) => void;
}

export const CreateSessionModal: React.FC<CreateSessionModalProps> = ({
  isOpen,
  onClose,
  onSessionCreated,
}) => {
  const [title, setTitle] = useState("");
  const [inspectorName, setInspectorName] = useState("");
  const [assetTag, setAssetTag] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !inspectorName.trim()) {
      setError("Title and Inspector Name are required.");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const session = await createSession({
        title: title.trim(),
        inspector_name: inspectorName.trim(),
        asset_tag: assetTag.trim() || undefined,
      });
      onSessionCreated(session);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to create session.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-header">
          <h3 style={{ fontSize: "1.1rem", fontWeight: "700" }}>Start New Inspection Session</h3>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          {error && (
            <div style={{ color: "#ef4444", fontSize: "0.85rem", background: "rgba(239, 68, 68, 0.1)", padding: "8px 12px", borderRadius: "6px" }}>
              {error}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Inspection Title *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Gas Turbine Combustion Chamber #2"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Lead Inspector Name *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Dr. Sarah Lin (Level III NDT)"
              value={inspectorName}
              onChange={(e) => setInspectorName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Asset / Component Tag (Optional)</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. GT-800-STAGE-1-BLADE"
              value={assetTag}
              onChange={(e) => setAssetTag(e.target.value)}
            />
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              <Check size={16} />
              {loading ? "Creating..." : "Create Session"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
