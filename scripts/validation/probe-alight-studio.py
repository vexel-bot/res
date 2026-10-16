"""Read the real Studio API using only the existing isolated study identity.

Does not create users, mutate documents, render, or expose credentials.
"""

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import Membership, User, Workspace  # noqa: E402
from app.security import create_access_token  # noqa: E402


def main():
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "motion-study-20261001@example.com"))
        workspace = db.get(Workspace, "4812f2c0-1a2a-4f6d-967d-17b370c8d849")
        if not user or not workspace or workspace.name != "Laboratório Motion 01-10":
            raise ValueError("isolated_study_identity_required")
        membership = db.scalar(select(Membership).where(
            Membership.user_id == user.id, Membership.workspace_id == workspace.id,
        ))
        if not membership or membership.role.lower() not in {"owner", "admin"}:
            raise ValueError("isolated_study_owner_required")
        token = create_access_token(user.id)
        path = f"/api/v1/studios/v1/workspaces/{workspace.id}/render-engines"
    request = Request("http://127.0.0.1:3000" + path, headers={"Authorization": "Bearer " + token})
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
        status_code = response.status
    alight = next(engine for engine in data["engines"] if engine["provider"] == "alight-motion.contextual-v1")
    observation = {
        "kind": "studio.alight_connection_api_observation.v1",
        "httpStatus": status_code,
        "endpoint": path,
        "identityScope": "existing_isolated_study_owner",
        "apiResponse": alight,
        "silentFallback": data["silentFallback"],
        "apiSpendUsd": 0,
        "realAlightJobs": 0,
        "visualApproval": "not_assessed",
    }
    destination = ROOT / "output/alight-discovery-20261002/studio/api-observation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(observation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"httpStatus": status_code, "application": alight.get("applicationProbe"),
                      "renderAvailable": alight["available"], "blockers": alight["blockers"]}))


if __name__ == "__main__":
    main()
