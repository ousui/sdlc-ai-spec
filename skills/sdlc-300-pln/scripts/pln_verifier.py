"""PLN-specific persisted Artifact semantic verification."""
from __future__ import annotations

from packages.sdlc_runtime.canonical import require_single_table

from pln_common import WORK_HEADERS, PlnError

def semantic_validate(parsed, revision):
    work = require_single_table(parsed, WORK_HEADERS, "PLN Work Items")
    identities = tuple(row["ID"] for row in work.rows if row["ID"] != "None")
    if identities and identities != tuple(f"WI-{index:03d}" for index in range(1, len(identities)+1)):
        raise PlnError("persisted Work Item IDs are not stable sequential WI-NNN values")
    if any("status" in header.casefold() or "parallel" in header.casefold() for header in work.headers):
        raise PlnError("PLN Work Item table contains live execution state")
