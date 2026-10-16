#!/usr/bin/env python3
"""Evaluate whether local dataset evidence satisfies KeeAInu's training gate.

This is a fail-closed checklist, not a legal opinion or proof that labels are
correct. It never downloads data, changes source files, or starts training.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
INTENDED_USE_TO_LICENSE = {
    "evaluation": {"approved-for-evaluation", "approved-for-noncommercial-research", "approved-for-commercial-use"},
    "noncommercial-research": {"approved-for-noncommercial-research", "approved-for-commercial-use"},
    "commercial-training": {"approved-for-commercial-use"},
}
REVIEW_FIELDS = (
    "annotation_review_status",
    "class_mapping_review_status",
    "split_review_status",
)
APPROVED = "approved"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def assess_training_gate(
    audit: dict[str, Any],
    manifest: dict[str, Any],
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(ok), "detail": detail})

    dataset_id = manifest.get("dataset_id")
    check("dataset_id_matches", bool(dataset_id) and dataset_id == audit.get("dataset_id"),
          "Manifest and archive audit must identify the same dataset.")
    version = manifest.get("dataset_version")
    check("exact_dataset_version", isinstance(version, str) and version.strip() not in {"", "unknown", "latest"},
          "Pin the exact publisher/export version; 'latest' is not reproducible.")
    source_url = manifest.get("source_url")
    check("source_url_matches", isinstance(source_url, str) and source_url.startswith("https://")
          and source_url == audit.get("source_url"),
          "Use the same canonical HTTPS source URL in the audit and manifest.")
    archive_hash = manifest.get("archive_sha256")
    check("archive_hash_matches", isinstance(archive_hash, str) and bool(HEX_SHA256.fullmatch(archive_hash))
          and archive_hash == audit.get("archive_sha256"),
          "Manifest SHA-256 must match the immutable source archive audit.")
    license_id = manifest.get("license_id")
    check("license_identified", isinstance(license_id, str) and bool(license_id.strip())
          and license_id.lower() not in {"unknown", "unspecified", "none"},
          "Record the exact license or explicit written permission reference.")

    intended_use = manifest.get("intended_use")
    license_status = manifest.get("license_review_status")
    allowed_statuses = INTENDED_USE_TO_LICENSE.get(intended_use, set())
    check("rights_approved_for_intended_use", license_status in allowed_statuses,
          "Human-reviewed license status must authorize the specific intended use.")
    check("attribution_plan_recorded", isinstance(manifest.get("attribution"), str)
          and bool(manifest["attribution"].strip()),
          "Record the required attribution text or a reasoned 'not required' determination.")
    check("reviewer_recorded", isinstance(manifest.get("reviewer"), str)
          and bool(manifest["reviewer"].strip())
          and isinstance(manifest.get("reviewed_at"), str) and bool(manifest["reviewed_at"].strip()),
          "Record who reviewed the dataset and when.")

    for field in REVIEW_FIELDS:
        check(field, manifest.get(field) == APPROVED,
              f"{field} must be explicitly approved by a human reviewer.")
    check("target_task_recorded", manifest.get("target_task") in {
        "object-detection", "instance-segmentation", "semantic-segmentation", "classification"
    }, "Choose one target task; do not mix incompatible annotation types.")
    classes = manifest.get("class_names")
    check("class_mapping_present", isinstance(classes, list) and len(classes) > 0
          and all(isinstance(item, str) and item.strip() for item in classes)
          and len({item.strip() for item in classes}) == len(classes),
          "Provide unique, explicit target class names in stable order.")

    if validation is not None:
        check("validation_is_detection_task", validation.get("task") == "yolo-object-detection"
              and manifest.get("target_task") == "object-detection",
              "The current validator supports YOLO object detection only.")
        check("validation_has_no_structural_issues",
              validation.get("readiness") == "STRUCTURAL_CHECKS_PASSED_REVIEW_STILL_REQUIRED"
              and validation.get("missing_label_count") == 0
              and validation.get("unpaired_label_count") == 0
              and validation.get("label_error_count") == 0
              and validation.get("cross_split_exact_duplicate_count") == 0,
              "Resolve missing/orphan labels, malformed boxes and exact duplicates across splits.")

    passed = all(item["passed"] for item in checks)
    return {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "intended_use": intended_use,
        "gate_status": "CHECKLIST_PASSED_REQUIRES_INDEPENDENT_SIGNOFF" if passed else "BLOCKED",
        "checks_passed": sum(1 for item in checks if item["passed"]),
        "checks_total": len(checks),
        "checks": checks,
        "limitations": [
            "This checklist does not independently verify license claims, annotation truth, class semantics, or reviewer authority.",
            "A passed checklist is not a guarantee of model quality or production/safety suitability.",
            "Real target-device footage and a held-out, sequence-separated evaluation remain required."
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True, help="JSON report from audit_archive.py.")
    parser.add_argument("--manifest", required=True, help="Human-completed dataset review manifest JSON.")
    parser.add_argument("--validation", help="Optional JSON report from validate_yolo_dataset.py.")
    parser.add_argument("--output", required=True, help="Path to write gate result JSON.")
    args = parser.parse_args()
    try:
        audit = load_json(Path(args.audit))
        manifest = load_json(Path(args.manifest))
        validation = load_json(Path(args.validation)) if args.validation else None
        result = assess_training_gate(audit, manifest, validation)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({
            "gate_status": result["gate_status"],
            "checks_passed": result["checks_passed"],
            "checks_total": result["checks_total"],
            "report": str(output),
        }, indent=2))
        return 0 if result["gate_status"] != "BLOCKED" else 1
    except (OSError, ValueError) as exc:
        print(f"GATE_FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
