"""Register every packaged contractor at package-v2, then run the installer."""

import hashlib
import json
import tempfile
from pathlib import Path

from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce import known_installer as ki
from agency_runtime.core.workforce.known_contractors import KNOWN_CONTRACTORS_BY_SLUG

tmp = Path(tempfile.mkdtemp()) / "agency.db"
store = Store(tmp)
for slug in sorted(KNOWN_CONTRACTORS_BY_SLUG):
    pkg = ki._v2_known_contractor_package(slug)
    version_id = store.stage_agency_workforce_agent(pkg.agent)
    evidence = ki.packaged_hiring_evidence(pkg)
    doc = pkg.workforce_contract.to_dict()
    case = store.create_hiring_case(
        case_type="hire",
        proposed_slug=slug,
        work_unit_id=f"known-{slug}",
        request_hash=ki._request_hash(pkg),
        contract_evidence=doc,
        contract_hash=hashlib.sha256(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
                "utf-8"
            )
        ).hexdigest(),
        **evidence,
    )
    if case["status"] == "proposed":
        case = store.transition_hiring_case(case["id"], status="audited")
    store.register_workforce_worker(
        agent_slug=slug,
        display_name=pkg.employment_contract.role,
        origin="agency",
        employment_class="contractor",
        agent_version_id=version_id,
        recruitment_contract=doc,
        relation="generated",
        hiring_case_id=case["id"],
    )

seeded = store.get_workforce_workers_by_slugs(
    tuple(sorted(KNOWN_CONTRACTORS_BY_SLUG)), disabled_agents=()
)
print("seeded workers at:", sorted({w["current_version"].split("-")[1] for w in seeded.values()}))
r = ki.install_known_contractors(store)
print(
    f"installed={len(r.installed)} upgraded={len(r.upgraded)} already_current={len(r.existing)} preserved={len(r.preserved)}"
)
after = store.get_workforce_workers_by_slugs(
    tuple(sorted(KNOWN_CONTRACTORS_BY_SLUG)), disabled_agents=()
)
print("workers now at:", sorted({w["current_version"].split("-")[1] for w in after.values()}))
