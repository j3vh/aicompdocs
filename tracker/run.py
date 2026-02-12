#!/usr/bin/env python3
"""Main entry point for the Algorithm Registry change tracker.

Usage:
    python -m tracker.run              # Fetch, detect changes, generate pages
    python -m tracker.run --fetch-only # Only fetch and store a snapshot
    python -m tracker.run --generate   # Only regenerate Jekyll pages from DB
"""

import argparse
import logging
import sys

from . import db
from .detect_changes import detect_changes
from .fetch import fetch_all_algorithms, get_lars_key
from .generate_pages import generate_all

logger = logging.getLogger(__name__)


def run_fetch_and_detect(conn) -> dict:
    """Fetch current data and detect changes against the previous snapshot."""
    algorithms = fetch_all_algorithms()
    if not algorithms:
        logger.error("No algorithms fetched. Aborting.")
        return {"error": "No data fetched"}

    # Create new snapshot
    snapshot_id = db.create_snapshot(conn, len(algorithms))
    logger.info("Created snapshot #%d with %d algorithms", snapshot_id, len(algorithms))

    # Store all algorithms
    current = {}
    for algo in algorithms:
        lars = get_lars_key(algo)
        if not lars:
            continue
        db.store_algorithm(conn, snapshot_id, lars, algo)
        current[lars] = algo

    conn.commit()
    logger.info("Stored %d algorithms in snapshot #%d", len(current), snapshot_id)

    # Get previous snapshot for comparison
    prev_id = db.get_previous_snapshot_id(conn, snapshot_id)
    if prev_id is None:
        logger.info("First snapshot - no previous data to compare against")
        return {
            "snapshot_id": snapshot_id,
            "total": len(current),
            "first_run": True,
        }

    previous = db.get_algorithms_for_snapshot(conn, prev_id)
    logger.info("Comparing against snapshot #%d (%d algorithms)", prev_id, len(previous))

    summary = detect_changes(conn, snapshot_id, current, previous)
    logger.info(
        "Changes: +%d added, ~%d modified, -%d removed, =%d unchanged",
        summary["added"],
        summary["modified"],
        summary["removed"],
        summary["unchanged"],
    )

    return {
        "snapshot_id": snapshot_id,
        "total": len(current),
        **summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Algorithm Registry Change Tracker")
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Only fetch and store, don't generate pages",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Only regenerate pages from existing DB",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    db_path = db.DB_PATH
    if args.db_path:
        from pathlib import Path
        db_path = Path(args.db_path)

    conn = db.get_connection(db_path)
    db.init_db(conn)

    try:
        if args.generate:
            logger.info("Regenerating pages from database...")
            generate_all(conn)
        elif args.fetch_only:
            result = run_fetch_and_detect(conn)
            logger.info("Result: %s", result)
        else:
            result = run_fetch_and_detect(conn)
            logger.info("Result: %s", result)
            if "error" not in result:
                generate_all(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
