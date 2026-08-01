#!/usr/bin/env python3
"""Validate the TechFlow threat model and data lifecycle policy."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ID_PATTERNS = {
    "asset": re.compile(r"A\d{2}$"),
    "boundary": re.compile(r"TB\d{2}$"),
    "control": re.compile(r"C\d{2}$"),
    "threat": re.compile(r"T\d{2}$"),
    "classification": re.compile(r"D[0-3]$"),
    "retention": re.compile(r"R\d{2}$"),
}


def ids(items: list[dict[str, Any]], kind: str, errors: list[str]) -> set[str]:
    values = [str(item.get("id", "")) for item in items]
    if len(values) != len(set(values)):
        errors.append(f"{kind}: duplicate ids")
    for value in values:
        if not ID_PATTERNS[kind].fullmatch(value):
            errors.append(f"{kind}: invalid id {value!r}")
    return set(values)


def require_fields(item: dict[str, Any], fields: tuple[str, ...], prefix: str, errors: list[str]) -> None:
    for field in fields:
        if field not in item or item[field] in (None, "", []):
            errors.append(f"{prefix}: missing {field}")


def validate_document(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in (
        "schemaVersion",
        "issue",
        "status",
        "riskModel",
        "assets",
        "trustBoundaries",
        "controls",
        "threats",
        "classifications",
        "retentionPolicies",
        "deletionPolicy",
        "legalHold",
        "ragP1Gate",
    ):
        if field not in data:
            errors.append(f"document: missing {field}")
    if errors:
        return errors

    asset_ids = ids(data["assets"], "asset", errors)
    boundary_ids = ids(data["trustBoundaries"], "boundary", errors)
    control_ids = ids(data["controls"], "control", errors)
    ids(data["threats"], "threat", errors)
    class_ids = ids(data["classifications"], "classification", errors)
    ids(data["retentionPolicies"], "retention", errors)

    bands = data["riskModel"].get("bands", [])
    expected_minimum = 1
    for band in bands:
        require_fields(band, ("name", "minimum", "maximum"), "risk band", errors)
        if band.get("minimum") != expected_minimum:
            errors.append(f"risk band {band.get('name')}: non-contiguous minimum")
        expected_minimum = int(band.get("maximum", 0)) + 1
    if expected_minimum != 26:
        errors.append("risk bands must cover 1 through 25")

    for boundary in data["trustBoundaries"]:
        require_fields(boundary, ("id", "from", "to", "requiredControls"), f"boundary {boundary.get('id')}", errors)
        unknown = set(boundary.get("requiredControls", [])) - control_ids
        if unknown:
            errors.append(f"boundary {boundary.get('id')}: unknown controls {sorted(unknown)}")

    for threat in data["threats"]:
        prefix = f"threat {threat.get('id')}"
        require_fields(
            threat,
            (
                "id",
                "name",
                "assets",
                "boundaries",
                "likelihood",
                "impact",
                "controls",
                "residualLikelihood",
                "residualImpact",
                "tests",
            ),
            prefix,
            errors,
        )
        unknown_assets = set(threat.get("assets", [])) - asset_ids
        unknown_boundaries = set(threat.get("boundaries", [])) - boundary_ids
        unknown_controls = set(threat.get("controls", [])) - control_ids
        if unknown_assets:
            errors.append(f"{prefix}: unknown assets {sorted(unknown_assets)}")
        if unknown_boundaries:
            errors.append(f"{prefix}: unknown boundaries {sorted(unknown_boundaries)}")
        if unknown_controls:
            errors.append(f"{prefix}: unknown controls {sorted(unknown_controls)}")
        for field in ("likelihood", "impact", "residualLikelihood", "residualImpact"):
            value = threat.get(field)
            if not isinstance(value, int) or not 1 <= value <= 5:
                errors.append(f"{prefix}: {field} must be 1..5")
        if isinstance(threat.get("residualLikelihood"), int) and isinstance(threat.get("residualImpact"), int):
            if threat["residualLikelihood"] * threat["residualImpact"] > 9:
                errors.append(f"{prefix}: residual risk exceeds MEDIUM")

    expected_classes = {"D0": ("PUBLIC", 0), "D1": ("INTERNAL", 1), "D2": ("CONFIDENTIAL", 2), "D3": ("RESTRICTED", 3)}
    actual_classes = {item.get("id"): (item.get("name"), item.get("rank")) for item in data["classifications"]}
    if actual_classes != expected_classes:
        errors.append("classifications must be D0 PUBLIC through D3 RESTRICTED")

    retention_by_id = {item.get("id"): item for item in data["retentionPolicies"]}
    for policy in data["retentionPolicies"]:
        prefix = f"retention {policy.get('id')}"
        require_fields(policy, ("id", "dataType", "classification", "collectionDefault", "deletion"), prefix, errors)
        if policy.get("classification") not in class_ids:
            errors.append(f"{prefix}: unknown classification")
        days = policy.get("retentionDays")
        if days is None and not policy.get("retentionRule"):
            errors.append(f"{prefix}: null retentionDays requires retentionRule")
        if days is not None and (not isinstance(days, int) or days < 0):
            errors.append(f"{prefix}: retentionDays must be a non-negative integer or null")
        if policy.get("classification") == "D3" and policy.get("collectionDefault") is not False:
            errors.append(f"{prefix}: D3 collectionDefault must be false")

    fixed = {"R01": 0, "R07": 7, "R08": 30, "R17": 0, "R18": 0}
    for policy_id, expected in fixed.items():
        if retention_by_id.get(policy_id, {}).get("retentionDays") != expected:
            errors.append(f"{policy_id}: retentionDays must be {expected}")
    raw_ai = retention_by_id.get("R13", {})
    if raw_ai.get("retentionDays", 999) > 30 or raw_ai.get("collectionDefault") is not False:
        errors.append("R13: raw AI data must be opt-in and retained no longer than 30 days")

    deletion = data["deletionPolicy"]
    if deletion.get("primaryAndDerivedSloDays", 999) > 7:
        errors.append("deletionPolicy: primary and derived deletion SLO must be at most 7 days")
    required_stores = {"chunks", "embeddings", "caches", "evaluation-links"}
    if not required_stores.issubset(set(deletion.get("derivedStores", []))):
        errors.append("deletionPolicy: derived stores are incomplete")

    legal_hold = data["legalHold"]
    if set(legal_hold.get("requiredApprovers", [])) != {"product-owner", "security-owner"}:
        errors.append("legalHold: product and security approvals are required")
    if legal_hold.get("maximumReviewIntervalDays", 999) > 90:
        errors.append("legalHold: review interval must be at most 90 days")

    gate = data["ragP1Gate"]
    if set(gate.get("defaultAllowedClassifications", [])) != {"D0"}:
        errors.append("ragP1Gate: only D0 may be allowed by default")
    if set(gate.get("conditionalClassifications", [])) != {"D1"}:
        errors.append("ragP1Gate: D1 must be conditional")
    if set(gate.get("deniedClassifications", [])) != {"D2", "D3"}:
        errors.append("ragP1Gate: D2 and D3 must be denied")
    unknown_gate_controls = set(gate.get("requiredControls", [])) - control_ids
    if unknown_gate_controls:
        errors.append(f"ragP1Gate: unknown controls {sorted(unknown_gate_controls)}")
    for field in ("sourceId", "owner", "classification", "version", "contentHash", "retentionPolicyId"):
        if field not in gate.get("requiredMetadata", []):
            errors.append(f"ragP1Gate: missing metadata {field}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("policy", type=Path)
    args = parser.parse_args()
    data = json.loads(args.policy.read_text(encoding="utf-8"))
    errors = validate_document(data)
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print(
        "policy=valid "
        f"threats={len(data['threats'])} controls={len(data['controls'])} "
        f"classifications={len(data['classifications'])} retention={len(data['retentionPolicies'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
