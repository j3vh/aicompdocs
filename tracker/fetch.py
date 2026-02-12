"""Fetch algorithm data from the Dutch Algorithm Registry API."""

import csv
import io
import json
import logging
import sys
import time

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://algoritmes.overheid.nl/api"
TIMEOUT = 60


def fetch_json_export() -> dict | None:
    """Fetch the full JSON site-data export."""
    url = f"{BASE_URL}/downloads/site-data/json"
    logger.info("Fetching JSON export from %s", url)
    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("JSON export failed: %s", e)
        return None


def fetch_csv_export(language: str = "NLD") -> list[dict] | None:
    """Fetch the CSV export and return as list of dicts."""
    url = f"{BASE_URL}/downloads/{language}"
    params = {"filetype": "csv"}
    logger.info("Fetching CSV export from %s", url)
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        return list(reader)
    except requests.RequestException as e:
        logger.warning("CSV export failed: %s", e)
        return None


def fetch_algorithm_page(language: str = "NLD", page: int = 0, limit: int = 100) -> dict | None:
    """Fetch a page of algorithms using the POST query endpoint."""
    url = f"{BASE_URL}/algoritme/{language}"
    payload = {"page": page, "limit": limit}
    logger.info("Fetching algorithm page %d (limit=%d)", page, limit)
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("Algorithm page fetch failed: %s", e)
        return None


def fetch_all_algorithms_paginated(language: str = "NLD", limit: int = 100) -> list[dict]:
    """Fetch all algorithms using pagination."""
    all_algorithms = []
    page = 0

    while True:
        data = fetch_algorithm_page(language, page, limit)
        if not data:
            break

        results = data.get("results", data.get("algorithms", []))
        if not results:
            break

        all_algorithms.extend(results)
        total = data.get("total_count", data.get("total", 0))
        logger.info("Fetched page %d: %d results (total: %d)", page, len(results), total)

        if len(all_algorithms) >= total or len(results) < limit:
            break

        page += 1
        time.sleep(0.5)

    return all_algorithms


def fetch_all_algorithms() -> list[dict]:
    """Fetch all algorithms, trying multiple methods in order of preference.

    Returns a list of algorithm dicts, each with at least a 'lars' key.
    """
    # Method 1: JSON site-data export (most complete)
    data = fetch_json_export()
    if data:
        algorithms = data.get("algorithms", data.get("results", []))
        if algorithms:
            logger.info("Got %d algorithms from JSON export", len(algorithms))
            return algorithms

    # Method 2: CSV export
    rows = fetch_csv_export("NLD")
    if rows:
        logger.info("Got %d algorithms from CSV export", len(rows))
        return rows

    # Method 3: Paginated API
    algorithms = fetch_all_algorithms_paginated("NLD")
    if algorithms:
        logger.info("Got %d algorithms from paginated API", len(algorithms))
        return algorithms

    logger.error("All fetch methods failed")
    return []


def get_lars_key(algo: dict) -> str:
    """Extract the LARS identifier from an algorithm dict."""
    return str(
        algo.get("lars", algo.get("lars_id", algo.get("algoritme_id", algo.get("id", ""))))
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    algorithms = fetch_all_algorithms()
    print(f"Fetched {len(algorithms)} algorithms")
    if algorithms:
        sample = algorithms[0]
        print(f"Sample keys: {list(sample.keys())[:15]}")
        print(json.dumps(sample, indent=2, ensure_ascii=False, default=str)[:1000])
