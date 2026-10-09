import React, { useState, useEffect } from "react";
import {
  BarChart3,
  Play,
  ShieldCheck,
  Layers,
  FileSpreadsheet
} from "lucide-react";
import {
  runEvaluationBenchmark,
  fetchEvaluationRuns,
  fetchEvaluationReport
} from "../services/api";
import {
  EvaluationReport
} from "../types/platform";

export const EvaluationBenchmarkView: React.FC = () => {
  const [runs, setRuns] = useState<any[]>([]);
  const [activeReport, setActiveReport] = useState<EvaluationReport | null>(null);
  const [evaluating, setEvaluating] = useState(false);

  // Eval Run Config states
  const [runName, setRunName] = useState("Mechanical Borescope Baseline Benchmark");
  const [splitStrategy, setSplitStrategy] = useState("ASSET_SESSION_SPLIT");
  const [trainRatio] = useState(0.70);
  const [valRatio] = useState(0.15);
  const [testRatio] = useState(0.15);
  const [syntheticHandling, setSyntheticHandling] = useState("EXCLUDE_FROM_EVAL");
  const [evaluatorName, setEvaluatorName] = useState("Validation Lead Engineer");

  const loadRuns = async () => {
    try {
      const data = await fetchEvaluationRuns();
      setRuns(data);
      if (data.length > 0 && !activeReport) {
        const full = await fetchEvaluationReport(data[0].id);
        setActiveReport(full);
      }
    } catch (err) {
      console.error("Failed to load evaluation runs:", err);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleExecuteBenchmark = async () => {
    try {
      setEvaluating(true);
      const report = await runEvaluationBenchmark({
        name: runName,
        target_equipment_families: [
          "ENGINES_TURBINES",
          "GEARBOXES_TRANSMISSIONS",
          "OTHER_MECHANICAL_ASSEMBLIES"
        ],
        split_strategy: splitStrategy,
        train_ratio: trainRatio,
        val_ratio: valRatio,
        test_ratio: testRatio,
        synthetic_handling: syntheticHandling,
        min_samples_threshold: 1,
        random_seed: 42,
        evaluator_identity: evaluatorName
      });
      setActiveReport(report);
      await loadRuns();
      alert("Evaluation benchmark run completed without data leakage.");
    } catch (err: any) {
      alert(`Evaluation failed: ${err.message || err}`);
    } finally {
      setEvaluating(false);
    }
  };

  const handleSelectRun = async (runId: string) => {
    try {
      const full = await fetchEvaluationReport(runId);
      setActiveReport(full);
    } catch (err) {
      alert(`Failed to load report: ${err}`);
    }
  };

  return (
    <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "24px", overflowY: "auto", height: "100%" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #1f293d", paddingBottom: "16px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "700", color: "#f8fafc", margin: "0 0 6px 0", display: "flex", alignItems: "center", gap: "10px" }}>
            <BarChart3 color="#38bdf8" /> Equipment-Aware Evaluation & Benchmarking
          </h2>
          <p style={{ color: "#94a3b8", margin: 0, fontSize: "0.9rem" }}>
            Audit models and detection pipelines with zero temporal frame leakage, synthetic segregation, and transparent metric validity.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: "24px" }}>
        {/* Left: Configuration & Controls */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Benchmark Trigger Form */}
          <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
            <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 14px 0", display: "flex", alignItems: "center", gap: "8px" }}>
              <Play size={18} color="#4ade80" /> Execute Evaluation Run
            </h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Benchmark Run Name</label>
                <input
                  type="text"
                  value={runName}
                  onChange={(e) => setRunName(e.target.value)}
                  style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                  Leakage Prevention Split Strategy
                </label>
                <select
                  value={splitStrategy}
                  onChange={(e) => setSplitStrategy(e.target.value)}
                  style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                >
                  <option value="ASSET_SESSION_SPLIT">Asset / Session Split (Guaranteed No Video Frame Leakage)</option>
                  <option value="EQUIPMENT_INSTANCE_SPLIT">Equipment Serial Split</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                  Synthetic Data Handling
                </label>
                <select
                  value={syntheticHandling}
                  onChange={(e) => setSyntheticHandling(e.target.value)}
                  style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                >
                  <option value="EXCLUDE_FROM_EVAL">Strictly Exclude Synthetic from Evaluation</option>
                  <option value="SYNTHETIC_BENCHMARK_ONLY">Synthetic Stress Test Benchmark Only</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: "0.8rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>Evaluator Identity</label>
                <input
                  type="text"
                  value={evaluatorName}
                  onChange={(e) => setEvaluatorName(e.target.value)}
                  style={{ width: "100%", background: "#070a13", border: "1px solid #334155", borderRadius: "6px", padding: "8px 12px", color: "#f8fafc", fontSize: "0.85rem" }}
                />
              </div>

              <button
                onClick={handleExecuteBenchmark}
                disabled={evaluating}
                style={{
                  marginTop: "8px",
                  background: "#2563eb",
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
                <Play size={16} /> Run Evaluation Benchmark
              </button>
            </div>
          </div>

          {/* Historic Runs List */}
          <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
            <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 12px 0", display: "flex", alignItems: "center", gap: "8px" }}>
              <FileSpreadsheet size={18} color="#fbbf24" /> Benchmark Runs ({runs.length})
            </h3>

            {runs.length === 0 ? (
              <div style={{ color: "#64748b", fontSize: "0.85rem" }}>No runs recorded yet. Execute one above.</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {runs.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => handleSelectRun(r.id)}
                    style={{
                      padding: "10px",
                      borderRadius: "6px",
                      cursor: "pointer",
                      background: activeReport?.run_id === r.id ? "#1e293b" : "#070a13",
                      border: activeReport?.run_id === r.id ? "1px solid #38bdf8" : "1px solid #1f293d",
                      fontSize: "0.85rem"
                    }}
                  >
                    <div style={{ fontWeight: "600", color: "#f8fafc" }}>{r.run_name}</div>
                    <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "2px" }}>
                      Hash: {r.dataset_manifest_hash.slice(0, 16)}...
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#64748b", marginTop: "2px" }}>
                      {new Date(r.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Active Evaluation Report Details */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {!activeReport ? (
            <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "40px", textAlign: "center", color: "#94a3b8" }}>
              Select or execute an evaluation run to view equipment slices and metrics.
            </div>
          ) : (
            <>
              {/* Overall Summary KPI Cards */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
                <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "8px", padding: "14px" }}>
                  <div style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Assets Evaluated</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#f8fafc", marginTop: "4px" }}>
                    {activeReport.total_assets_evaluated}
                  </div>
                  <div style={{ color: "#4ade80", fontSize: "0.75rem", marginTop: "4px" }}>
                    {activeReport.real_samples_count} Real Samples
                  </div>
                </div>

                <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "8px", padding: "14px" }}>
                  <div style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Precision</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#38bdf8", marginTop: "4px" }}>
                    {activeReport.overall_classification.precision != null
                      ? `${(activeReport.overall_classification.precision * 100).toFixed(1)}%`
                      : "N/A"}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: "0.75rem", marginTop: "4px" }}>
                    Status: {activeReport.overall_classification.status}
                  </div>
                </div>

                <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "8px", padding: "14px" }}>
                  <div style={{ color: "#94a3b8", fontSize: "0.8rem" }}>Recall</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#fbbf24", marginTop: "4px" }}>
                    {activeReport.overall_classification.recall != null
                      ? `${(activeReport.overall_classification.recall * 100).toFixed(1)}%`
                      : "N/A"}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: "0.75rem", marginTop: "4px" }}>
                    TP: {activeReport.overall_classification.true_positives} | FN: {activeReport.overall_classification.false_negatives}
                  </div>
                </div>

                <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "8px", padding: "14px" }}>
                  <div style={{ color: "#94a3b8", fontSize: "0.8rem" }}>F1 Score</div>
                  <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#a855f7", marginTop: "4px" }}>
                    {activeReport.overall_classification.f1_score != null
                      ? activeReport.overall_classification.f1_score.toFixed(3)
                      : "N/A"}
                  </div>
                  <div style={{ color: "#94a3b8", fontSize: "0.75rem", marginTop: "4px" }}>
                    Support: {activeReport.overall_classification.support}
                  </div>
                </div>
              </div>

              {/* Equipment Family Slices Breakdown */}
              <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
                <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 14px 0", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Layers size={18} color="#38bdf8" /> Equipment Hierarchy Slices & Localization (IoU)
                </h3>

                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #1f293d", color: "#94a3b8", textAlign: "left" }}>
                      <th style={{ padding: "8px" }}>Equipment Family</th>
                      <th style={{ padding: "8px" }}>Samples</th>
                      <th style={{ padding: "8px" }}>Precision</th>
                      <th style={{ padding: "8px" }}>Recall</th>
                      <th style={{ padding: "8px" }}>F1 Score</th>
                      <th style={{ padding: "8px" }}>Mean IoU</th>
                      <th style={{ padding: "8px" }}>Validity Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeReport.equipment_slices.map((slice, idx) => (
                      <tr key={idx} style={{ borderBottom: "1px solid #161f36" }}>
                        <td style={{ padding: "8px", fontWeight: "600", color: "#f8fafc" }}>
                          {slice.equipment_family}
                        </td>
                        <td style={{ padding: "8px" }}>{slice.sample_count}</td>
                        <td style={{ padding: "8px", color: "#38bdf8" }}>
                          {slice.classification.precision != null ? `${(slice.classification.precision * 100).toFixed(1)}%` : "N/A"}
                        </td>
                        <td style={{ padding: "8px", color: "#fbbf24" }}>
                          {slice.classification.recall != null ? `${(slice.classification.recall * 100).toFixed(1)}%` : "N/A"}
                        </td>
                        <td style={{ padding: "8px", color: "#a855f7" }}>
                          {slice.classification.f1_score != null ? slice.classification.f1_score.toFixed(3) : "N/A"}
                        </td>
                        <td style={{ padding: "8px", color: "#4ade80" }}>
                          {slice.localization?.mean_iou != null
                            ? slice.localization.mean_iou.toFixed(2)
                            : "N/A"}
                        </td>
                        <td style={{ padding: "8px" }}>
                          <span style={{
                            padding: "2px 6px",
                            borderRadius: "4px",
                            fontSize: "0.75rem",
                            background: slice.classification.status === "VALID" ? "#064e3b" : "#451a03",
                            color: slice.classification.status === "VALID" ? "#34d399" : "#fb923c"
                          }}>
                            {slice.classification.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Confusion Matrix & Limitations */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                {/* Confusion Matrix */}
                <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
                  <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 14px 0" }}>
                    Defect Classification Matrix
                  </h3>
                  <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem", textAlign: "center" }}>
                      <thead>
                        <tr>
                          <th style={{ padding: "6px", color: "#94a3b8" }}>Ground Truth \ Pred</th>
                          {activeReport.confusion_matrix_labels.map((l) => (
                            <th key={l} style={{ padding: "6px", color: "#cbd5e1" }}>{l.slice(0, 6)}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {activeReport.confusion_matrix.map((row, rIdx) => (
                          <tr key={rIdx}>
                            <td style={{ padding: "6px", color: "#94a3b8", fontWeight: "600", textAlign: "left" }}>
                              {activeReport.confusion_matrix_labels[rIdx]?.slice(0, 6)}
                            </td>
                            {row.map((val, cIdx) => (
                              <td
                                key={cIdx}
                                style={{
                                  padding: "6px",
                                  background: rIdx === cIdx && val > 0 ? "#1e3a8a" : "#070a13",
                                  border: "1px solid #1f293d",
                                  color: rIdx === cIdx ? "#93c5fd" : "#64748b",
                                  fontWeight: val > 0 ? "700" : "400"
                                }}
                              >
                                {val}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Audit Safeguards & Limitations */}
                <div style={{ background: "#111827", border: "1px solid #1f293d", borderRadius: "10px", padding: "18px" }}>
                  <h3 style={{ fontSize: "1.05rem", fontWeight: "600", color: "#f8fafc", margin: "0 0 12px 0", display: "flex", alignItems: "center", gap: "8px" }}>
                    <ShieldCheck size={18} color="#4ade80" /> Integrity & Limitations
                  </h3>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.85rem", color: "#94a3b8" }}>
                    <div>
                      <strong style={{ color: "#f8fafc" }}>Manifest Hash:</strong>
                      <div style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#38bdf8", marginTop: "2px" }}>
                        {activeReport.dataset_manifest_hash}
                      </div>
                    </div>
                    <div>
                      <strong style={{ color: "#f8fafc" }}>Split Strategy:</strong> {activeReport.split_strategy}
                    </div>
                    <div style={{ marginTop: "6px" }}>
                      <strong style={{ color: "#f8fafc" }}>Audit Safeguards:</strong>
                      <ul style={{ margin: "4px 0 0 16px", padding: 0, color: "#cbd5e1", fontSize: "0.8rem" }}>
                        {activeReport.limitations.map((lim, i) => (
                          <li key={i} style={{ marginBottom: "4px" }}>{lim}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
