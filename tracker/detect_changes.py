"""Detect changes between two snapshots of algorithm data."""

import json
import logging

from . import db

logger = logging.getLogger(__name__)

# Fields to ignore when comparing (metadata that changes every fetch)
IGNORE_FIELDS = {"last_updated", "updated_at", "created_at", "id", "lars", "lars_id"}

# Fields considered significant for change reporting
KEY_FIELDS = {
    "name",
    "description_short",
    "organization",
    "organisation",
    "status",
    "publication_category",
    "category",
    "purpose_and_impact",
    "considerations",
    "human_intervention",
    "risk_management",
    "legal_basis",
    "data",
    "technical_operation",
    "supplier",
    "contact",
    "theme",
    "start_date",
    "end_date",
    "link",
    "source_code_link",
    "impact_assessments",
}


def normalize_value(value) -> str:
    """Normalize a value for comparison."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return str(value).strip()


def compare_algorithms(old: dict, new: dict) -> tuple[list[str], dict, dict]:
    """Compare two algorithm dicts and return changed fields with old/new values.

    Returns (changed_fields, old_values, new_values).
    """
    all_keys = set(old.keys()) | set(new.keys())
    relevant_keys = (all_keys - IGNORE_FIELDS) & KEY_FIELDS

    changed_fields = []
    old_values = {}
    new_values = {}

    for key in sorted(relevant_keys):
        old_val = normalize_value(old.get(key))
        new_val = normalize_value(new.get(key))
        if old_val != new_val:
            changed_fields.append(key)
            old_values[key] = old.get(key, "")
            new_values[key] = new.get(key, "")

    return changed_fields, old_values, new_values


def detect_changes(
    conn,
    snapshot_id: int,
    current_algorithms: dict[str, dict],
    previous_algorithms: dict[str, dict],
) -> dict:
    """Detect all changes between previous and current algorithm sets.

    Returns a summary dict with counts.
    """
    current_lars = set(current_algorithms.keys())
    previous_lars = set(previous_algorithms.keys())

    added = current_lars - previous_lars
    removed = previous_lars - current_lars
    common = current_lars & previous_lars

    summary = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}

    # New algorithms
    for lars in sorted(added):
        algo = current_algorithms[lars]
        name = algo.get("name", "")
        org = algo.get("organization", algo.get("organisation", ""))
        db.store_change(conn, snapshot_id, lars, name, org, "added")
        summary["added"] += 1
        logger.info("NEW: %s - %s (%s)", lars, name, org)

    # Removed algorithms
    for lars in sorted(removed):
        algo = previous_algorithms[lars]
        name = algo.get("name", "")
        org = algo.get("organization", algo.get("organisation", ""))
        db.store_change(conn, snapshot_id, lars, name, org, "removed")
        summary["removed"] += 1
        logger.info("REMOVED: %s - %s (%s)", lars, name, org)

    # Modified algorithms
    for lars in sorted(common):
        old = previous_algorithms[lars]
        new = current_algorithms[lars]
        changed_fields, old_values, new_values = compare_algorithms(old, new)

        if changed_fields:
            name = new.get("name", "")
            org = new.get("organization", new.get("organisation", ""))
            db.store_change(
                conn,
                snapshot_id,
                lars,
                name,
                org,
                "modified",
                changed_fields,
                old_values,
                new_values,
            )
            summary["modified"] += 1
            logger.info("MODIFIED: %s - %s (fields: %s)", lars, name, ", ".join(changed_fields))
        else:
            summary["unchanged"] += 1

    conn.commit()
    return summary
