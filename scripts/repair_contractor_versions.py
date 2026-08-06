"""Repair contractor version rows minted with a leaked ``sha256:`` prefix.

``known_installer`` used to build a contractor's version as
``contractor-{N}-{prompt_hash[:16]}`` without stripping the ``sha256:``
algorithm prefix, while ``hiring`` stripped it.  Identical prompt content
therefore registered under two different identities, and a contractor staged by
the packaged installer could not be resolved by a reference minted anywhere
else -- surfacing as a fatal preflight block.

The code defect is fixed at the source (``contractor_prompt_version``), but
already-registered rows keep the malformed spelling: ``install_known_contractors``
skips any slug that already has an Agency-owned worker, so a reinstall will not
refresh them on its own.

Run read-only first.  ``--apply`` requires an explicit backup path and writes
inside a single transaction.

    python scripts/repair_contractor_versions.py
    python scripts/repair_contractor_versions.py --apply --backup agency.db.bak

By default only the *resolution* tables are rewritten -- the rows that decide
whether a lookup succeeds.  Historical evidence tables record what actually
happened at the time and are left alone unless ``--include-history`` is passed;
rewriting them makes the audit trail claim an identity that was never used.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import sys
from pathlib import Path

MALFORMED = "contractor-%-sha256:%"

# (table, version column) pairs that determine whether a lookup resolves.
RESOLUTION_TARGETS = (
    ("agent_versions", "version"),
    ("agent_active", "version"),
    ("agent_workers", "current_version"),
)

# Append-only evidence describing what was used at the time.
HISTORY_TARGETS = (
    ("agent_worker_events", "version"),
    ("agent_performance_events", "version"),
    ("delegation_events", "retrieved_specialist_version"),
    ("delegation_activation_receipts", "specialist_version"),
    ("delegation_activation_consumptions", "specialist_version"),
)


def canonical_version(stored_version: str, prompt_hash: str) -> str:
    """Rebuild the correct version from the row's own full prompt hash."""

    template = stored_version.removeprefix("contractor-").split("-", 1)[0]
    digest = str(prompt_hash or "").removeprefix("sha256:")[:16]
    if not template.isdigit() or re.fullmatch(r"[0-9a-f]{16}", digest) is None:
        raise ValueError(f"cannot rebuild a canonical version from {stored_version!r}")
    return f"contractor-{template}-{digest}"


def build_mapping(conn: sqlite3.Connection) -> dict[str, str]:
    """Map every malformed version to its canonical form via agent_versions.hash."""

    mapping: dict[str, str] = {}
    rows = conn.execute(
        "SELECT DISTINCT agent_slug, version, hash FROM agent_versions WHERE version LIKE ?",
        (MALFORMED,),
    ).fetchall()
    for row in rows:
        stored = str(row["version"])
        correct = canonical_version(stored, str(row["hash"]))
        previous = mapping.get(stored)
        if previous is not None and previous != correct:
            raise SystemExit(
                f"ambiguous repair: {stored!r} maps to both {previous!r} and {correct!r}"
            )
        mapping[stored] = correct
    return mapping


def count_rows(conn: sqlite3.Connection, table: str, column: str, value: str) -> int:
    try:
        return int(
            conn.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" = ?',
                (value,),
            ).fetchone()[0]
        )
    except sqlite3.Error:
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="", help="path to agency.db (default: configured store)")
    parser.add_argument("--apply", action="store_true", help="write the repair")
    parser.add_argument("--backup", default="", help="backup path, required with --apply")
    parser.add_argument(
        "--include-history",
        action="store_true",
        help="also rewrite append-only evidence tables",
    )
    args = parser.parse_args()

    if args.db:
        db_path = Path(args.db)
    else:
        from agency_runtime.core.store.security import default_db_path

        db_path = Path(default_db_path())
    if not db_path.exists():
        print(f"no store at {db_path}", file=sys.stderr)
        return 2
    if args.apply and not args.backup:
        print("--apply requires --backup", file=sys.stderr)
        return 2

    targets = RESOLUTION_TARGETS + (HISTORY_TARGETS if args.include_history else ())

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        mapping = build_mapping(conn)
        if not mapping:
            print("no malformed contractor versions found")
            return 0

        print(f"store: {db_path}")
        print(f"{len(mapping)} malformed version(s) to repair\n")
        total = 0
        for stored, correct in sorted(mapping.items()):
            print(f"  {stored}  ->  {correct}")
            for table, column in targets:
                hits = count_rows(conn, table, column, stored)
                if hits:
                    print(f"      {table}.{column}: {hits}")
                    total += hits
        print(f"\ntotal rows affected: {total}")
        if not args.include_history:
            print("(resolution tables only; pass --include-history to rewrite evidence rows)")

        if not args.apply:
            print("\nDRY RUN -- nothing written. Re-run with --apply --backup <path>.")
            return 0

        shutil.copy2(db_path, args.backup)
        print(f"\nbackup written to {args.backup}")
        conn.execute("BEGIN IMMEDIATE")
        written = 0
        for stored, correct in mapping.items():
            for table, column in targets:
                try:
                    cursor = conn.execute(
                        f'UPDATE "{table}" SET "{column}" = ? WHERE "{column}" = ?',
                        (correct, stored),
                    )
                except sqlite3.Error as exc:
                    conn.rollback()
                    print(f"failed on {table}.{column}: {exc}", file=sys.stderr)
                    return 1
                written += cursor.rowcount if cursor.rowcount > 0 else 0
        conn.commit()
        print(f"repaired {written} row(s)")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
