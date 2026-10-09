import React, { useState, useRef } from "react";
import { UploadCloud, X, CheckCircle, AlertCircle, FileVideo } from "lucide-react";
import { uploadMedia } from "../services/api";
import { MediaItem } from "../types/inspection";

interface MediaUploadModalProps {
  isOpen: boolean;
  sessionId: string;
  onClose: () => void;
  onMediaUploaded: (media: MediaItem) => void;
}

export const MediaUploadModal: React.FC<MediaUploadModalProps> = ({
  isOpen,
  sessionId,
  onClose,
  onMediaUploaded,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      setError(null);
      const media = await uploadMedia(sessionId, selectedFile);
      onMediaUploaded(media);
      onClose();
    } catch (err: any) {
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-header">
          <h3 style={{ fontSize: "1.1rem", fontWeight: "700" }}>Upload Inspection Footage</h3>
          <button className="btn btn-secondary btn-sm" onClick={onClose} disabled={uploading}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          {error && (
            <div style={{ color: "#ef4444", fontSize: "0.85rem", background: "rgba(239, 68, 68, 0.1)", padding: "10px 14px", borderRadius: "6px", display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div
            className={`dropzone ${dragActive ? "drag-active" : ""}`}
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".mp4,.avi,.mov,.mkv,.jpg,.jpeg,.png,.bmp"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <UploadCloud size={36} color="#06b6d4" />
            <div>
              <strong style={{ color: "#f8fafc" }}>Click to browse</strong> or drag & drop inspection footage
            </div>
            <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
              Supported: MP4, AVI, MOV, MKV, JPG, PNG (Max 500MB)
            </span>
          </div>

          {selectedFile && (
            <div style={{ background: "var(--bg-surface)", padding: "12px", borderRadius: "8px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <FileVideo size={20} color="#06b6d4" />
                <div>
                  <div style={{ fontSize: "0.85rem", fontWeight: "600" }}>{selectedFile.name}</div>
                  <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </div>
                </div>
              </div>
              <CheckCircle size={18} color="#10b981" />
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={uploading}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!selectedFile || uploading}
              onClick={handleUpload}
            >
              {uploading ? "Ingesting & Preserving..." : "Upload & Ingest"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
