"""Generate Jekyll-compatible Markdown pages from tracked changes."""

import json
import logging
from datetime import datetime
from pathlib import Path

from . import db

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent.parent / "algoritmeregister"


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "wijzigingen").mkdir(exist_ok=True)


def format_date(iso_str: str) -> str:
    """Format an ISO date string for display."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d-%m-%Y %H:%M UTC")
    except (ValueError, TypeError):
        return iso_str or "Onbekend"


def format_date_short(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return iso_str or ""


def escape_md(text: str) -> str:
    """Escape pipe characters for Markdown tables."""
    if not text:
        return ""
    return str(text).replace("|", "\\|").replace("\n", " ")


def generate_index_page(conn) -> None:
    """Generate the main index page for the changelog section."""
    snapshots = db.get_all_snapshots(conn)
    all_changes = db.get_all_changes(conn)

    # Count by type
    added = sum(1 for c in all_changes if c["change_type"] == "added")
    removed = sum(1 for c in all_changes if c["change_type"] == "removed")
    modified = sum(1 for c in all_changes if c["change_type"] == "modified")

    lines = [
        "---",
        "layout: default",
        "title: Algoritmeregister Wijzigingen",
        "nav_order: 5",
        "has_children: true",
        "---",
        "",
        "# Algoritmeregister Wijzigingen",
        "",
        "Deze pagina toont wijzigingen in het [Algoritmeregister van de Nederlandse overheid]"
        "(https://algoritmes.overheid.nl/nl).",
        "",
        "Het Algoritmeregister wordt periodiek gecontroleerd op nieuwe, gewijzigde en "
        "verwijderde algoritme-registraties.",
        "",
        "## Samenvatting",
        "",
        f"| Statistiek | Aantal |",
        f"|---|---|",
        f"| Snapshots | {len(snapshots)} |",
        f"| Nieuwe registraties | {added} |",
        f"| Gewijzigde registraties | {modified} |",
        f"| Verwijderde registraties | {removed} |",
        f"| Totaal wijzigingen | {len(all_changes)} |",
        "",
    ]

    if snapshots:
        lines.extend([
            "## Recente snapshots",
            "",
            "| Datum | Aantal algoritmes | Wijzigingen |",
            "|---|---|---|",
        ])
        for snap in snapshots[:20]:
            changes = db.get_changes_for_snapshot(conn, snap["id"])
            date = format_date(snap["fetched_at"])
            change_summary = _change_summary(changes)
            slug = format_date_short(snap["fetched_at"])
            lines.append(
                f"| [{date}](wijzigingen/{slug}/) | {snap['total_algorithms']} | {change_summary} |"
            )
        lines.append("")

    if all_changes:
        lines.extend([
            "## Recente wijzigingen",
            "",
            "| Datum | Type | Algoritme | Organisatie |",
            "|---|---|---|---|",
        ])
        for change in all_changes[:30]:
            date = format_date(change.get("fetched_at", change["detected_at"]))
            ctype = _change_type_label(change["change_type"])
            name = escape_md(change.get("name", ""))
            org = escape_md(change.get("organization", ""))
            lars = change["lars"]
            lines.append(
                f"| {date} | {ctype} | [{name}](https://algoritmes.overheid.nl/nl/algoritme/{lars}) | {org} |"
            )
        lines.append("")

    (OUTPUT_DIR / "index.md").write_text("\n".join(lines), encoding="utf-8")
    logger.info("Generated index page")


def generate_snapshot_pages(conn) -> None:
    """Generate individual pages for each snapshot."""
    snapshots = db.get_all_snapshots(conn)

    for snap in snapshots:
        changes = db.get_changes_for_snapshot(conn, snap["id"])
        date = format_date(snap["fetched_at"])
        slug = format_date_short(snap["fetched_at"])

        lines = [
            "---",
            "layout: default",
            f"title: Wijzigingen {slug}",
            "parent: Algoritmeregister Wijzigingen",
            "---",
            "",
            f"# Wijzigingen gedetecteerd op {date}",
            "",
            f"**Totaal algoritmes in register:** {snap['total_algorithms']}",
            "",
        ]

        if not changes:
            lines.append("Geen wijzigingen gedetecteerd bij deze scan.")
        else:
            summary = _change_summary(changes)
            lines.append(f"**Samenvatting:** {summary}")
            lines.append("")

            # Group by type
            added = [c for c in changes if c["change_type"] == "added"]
            modified = [c for c in changes if c["change_type"] == "modified"]
            removed = [c for c in changes if c["change_type"] == "removed"]

            if added:
                lines.extend(_render_added_section(added))
            if modified:
                lines.extend(_render_modified_section(modified))
            if removed:
                lines.extend(_render_removed_section(removed))

        page_dir = OUTPUT_DIR / "wijzigingen"
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")
        logger.info("Generated snapshot page for %s", slug)


def _render_added_section(changes: list[dict]) -> list[str]:
    lines = [
        "## Nieuwe registraties",
        "",
        "| Algoritme | Organisatie | Categorie |",
        "|---|---|---|",
    ]
    for c in changes:
        name = escape_md(c.get("name", ""))
        org = escape_md(c.get("organization", ""))
        lars = c["lars"]
        lines.append(
            f"| [{name}](https://algoritmes.overheid.nl/nl/algoritme/{lars}) | {org} | |"
        )
    lines.append("")
    return lines


def _render_modified_section(changes: list[dict]) -> list[str]:
    lines = [
        "## Gewijzigde registraties",
        "",
    ]
    for c in changes:
        name = escape_md(c.get("name", ""))
        org = escape_md(c.get("organization", ""))
        lars = c["lars"]
        lines.append(
            f"### [{name}](https://algoritmes.overheid.nl/nl/algoritme/{lars})"
        )
        lines.append(f"**Organisatie:** {org}")
        lines.append("")

        changed_fields = json.loads(c["changed_fields"]) if c.get("changed_fields") else []
        old_values = json.loads(c["old_values"]) if c.get("old_values") else {}
        new_values = json.loads(c["new_values"]) if c.get("new_values") else {}

        if changed_fields:
            lines.append("| Veld | Oude waarde | Nieuwe waarde |")
            lines.append("|---|---|---|")
            for field in changed_fields:
                old = escape_md(str(old_values.get(field, "")))
                new = escape_md(str(new_values.get(field, "")))
                # Truncate long values for table display
                if len(old) > 100:
                    old = old[:100] + "..."
                if len(new) > 100:
                    new = new[:100] + "..."
                lines.append(f"| {field} | {old} | {new} |")
            lines.append("")

    return lines


def _render_removed_section(changes: list[dict]) -> list[str]:
    lines = [
        "## Verwijderde registraties",
        "",
        "| Algoritme | Organisatie |",
        "|---|---|",
    ]
    for c in changes:
        name = escape_md(c.get("name", ""))
        org = escape_md(c.get("organization", ""))
        lines.append(f"| {name} | {org} |")
    lines.append("")
    return lines


def _change_type_label(change_type: str) -> str:
    labels = {
        "added": "Nieuw",
        "modified": "Gewijzigd",
        "removed": "Verwijderd",
    }
    return labels.get(change_type, change_type)


def _change_summary(changes: list[dict]) -> str:
    added = sum(1 for c in changes if c["change_type"] == "added")
    modified = sum(1 for c in changes if c["change_type"] == "modified")
    removed = sum(1 for c in changes if c["change_type"] == "removed")
    parts = []
    if added:
        parts.append(f"+{added} nieuw")
    if modified:
        parts.append(f"~{modified} gewijzigd")
    if removed:
        parts.append(f"-{removed} verwijderd")
    return ", ".join(parts) if parts else "Geen wijzigingen"


def generate_all(conn) -> None:
    """Generate all Jekyll pages."""
    ensure_output_dir()
    generate_index_page(conn)
    generate_snapshot_pages(conn)
    logger.info("All pages generated in %s", OUTPUT_DIR)
