"""Validate the creative department corpus without converting discovery into evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "docs/studios/knowledge/creative-department-2026-10"
ANCHORS = {"alfredo-soares", "alex-hormozi"}
SUPPORT = {"ann-handley", "joe-pulizzi", "seth-godin", "april-dunford", "donald-miller", "andy-crestodina"}
AXES = {"intent", "audience", "problem", "thesis", "opening", "development", "evidence", "value", "cta", "visualLanguage", "strategy"}
KINDS = {"teaching", "observation", "interpretation", "clicko_hypothesis"}


def canonical(url):
    parsed = urlparse(url)
    if parsed.netloc in {"www.youtube.com", "youtube.com"} and parsed.path == "/watch":
        return "youtube:" + parse_qs(parsed.query).get("v", [""])[0]
    if "instagram.com" in parsed.netloc:
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2 and parts[-2] in {"p", "reel"}:
            return "instagram:" + parts[-1]
    return parsed.netloc.removeprefix("www.") + parsed.path.rstrip("/")


def read(folder, name):
    return json.loads((folder / name).read_text(encoding="utf-8"))


def validate(folder):
    errors = []
    candidates = read(folder, "candidates.json")
    cases = read(folder, "cases.json")["cases"]
    frameworks = read(folder, "frameworks.json")["frameworks"]
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate case ID")
    urls = [canonical(case["url"]) for case in cases]
    if len(urls) != len(set(urls)):
        errors.append("The same source was counted as multiple selected cases")
    if len(cases) != 36:
        errors.append(f"Expected 36 selected cases, got {len(cases)}")
    authors = Counter(c["author"] for c in cases)
    platforms = Counter((c["author"], c["platform"]) for c in cases)
    discovered = {}
    for author in ANCHORS:
        source = candidates["authors"][author]
        pool = {"youtube:" + row[0] for row in source["youtube"]}
        pool.update("instagram:" + row[0].strip("/").split("/")[-1] for row in source["instagramCandidates"])
        discovered[author] = len(pool)
        if len(pool) < 30:
            errors.append(f"{author}: fewer than 30 unique candidates")
        for platform in ("youtube", "instagram"):
            if platforms[(author, platform)] != 6:
                errors.append(f"{author}: expected six {platform} cases")
        for case in cases:
            if case["author"] == author and canonical(case["url"]) not in pool:
                errors.append(f"{case['id']}: selected source missing from discovery ledger")
    for author in SUPPORT:
        if authors[author] != 2:
            errors.append(f"{author}: expected two primary sources")
    if set(authors) != ANCHORS | SUPPORT:
        errors.append("Unexpected or missing author")
    gaps = []
    audiovisual_required = 0
    audiovisual_complete = 0
    for case in cases:
        cid = case["id"]
        if set(case["analysis"]) != AXES or not all(isinstance(v, str) and v.strip() for v in case["analysis"].values()):
            errors.append(f"{cid}: missing analytical axis")
        if not case.get("selectionReason") or not case.get("limitations") or not case.get("counterexample"):
            errors.append(f"{cid}: missing selection rationale, limitation or counterexample")
        if not case.get("notes") or any(n.get("kind") not in KINDS or not n.get("locator") or not n.get("text") for n in case["notes"]):
            errors.append(f"{cid}: untyped or unlocated evidence")
        if not case.get("coverage") or not all(k in case["coverage"] for k in ("text", "visual", "audio", "completeAudiovisual")):
            errors.append(f"{cid}: coverage not declared")
        if case["coverage"].get("completeAudiovisual"):
            if case["coverage"]["audio"] != "full-review" or case["coverage"]["visual"] != "full-review":
                errors.append(f"{cid}: full audiovisual coverage claimed without full audio and visual review")
        if case["platform"] == "youtube" or case.get("format") == "reel":
            audiovisual_required += 1
            if case["coverage"].get("completeAudiovisual"):
                audiovisual_complete += 1
            else:
                gaps.append({"caseId": cid, "modality": "audiovisual", "reason": "Full audiovisual review is not attested; inspect declared coverage"})
        elif case.get("format") == "carousel" and case["coverage"]["visual"] != "full-review":
            gaps.append({"caseId": cid, "modality": "visual", "reason": "Complete carousel visual review is not attested"})
        if case.get("status") == "access-gap":
            gaps.append({"caseId": cid, "reason": "Source access gap"})
        target = folder / "cases" / cid / "analysis.md"
        if not target.is_file() or not (target.parent / "shots.json").is_file():
            errors.append(f"{cid}: missing rendered analysis or coverage map")
        else:
            mapping = read(target.parent, "shots.json")
            if mapping.get("caseId") != cid or mapping.get("source") != case["url"] or mapping.get("coverage") != case["coverage"]:
                errors.append(f"{cid}: modality map disagrees with case record")
            if not mapping.get("locatedTextUnits"):
                errors.append(f"{cid}: missing located evidence in modality map")
            if case["url"] not in target.read_text(encoding="utf-8"):
                errors.append(f"{cid}: rendered analysis lost its source")
        integrity = case.get("sourceIntegrity", {})
        if integrity.get("primary") is not True or not integrity.get("hashScope"):
            errors.append(f"{cid}: source provenance missing")
        digest = integrity.get("sha256")
        if case["platform"] == "youtube" and not digest:
            errors.append(f"{cid}: caption checksum missing")
        if digest and (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
            errors.append(f"{cid}: malformed SHA-256")
        rights = case.get("rights", {})
        if rights.get("distributedSourceMedia") is not False or not rights.get("useScope"):
            errors.append(f"{cid}: research rights scope missing")
    fids = [f["id"] for f in frameworks]
    if len(fids) != len(set(fids)):
        errors.append("Duplicate framework ID")
    for framework in frameworks:
        if not framework.get("caseIds") or set(framework["caseIds"]) - set(ids):
            errors.append(f"{framework['id']}: invalid case references")
        if not framework.get("version") or not framework.get("limits") or not framework.get("acceptanceTest"):
            errors.append(f"{framework['id']}: missing version, limitations or acceptance test")
    forbidden = {".mp4", ".mp3", ".wav", ".webm", ".png", ".jpg", ".jpeg"}
    if any(path.suffix.lower() in forbidden for path in folder.rglob("*")):
        errors.append("Third-party media or screenshots persisted in distributed research corpus")
    reports = ["SYNTHESIS.md", "AGENT_APPLICATION.md", "EXPERIENCE_REQUIREMENTS.md", "EXERCISES.md", "SOFTWARE_REFERENCES.md", "FRAMEWORKS.md", "REVIEW_AND_GAPS.md"]
    for report in reports:
        if not (folder / report).is_file():
            errors.append(f"Missing {report}")
    exercises = read(folder, "exercises.json")["exercises"]
    expected = {(brand, goal) for brand in ("b2b-service", "retail", "expert") for goal in ("education", "authority", "offer")}
    if {(e["brandType"], e["goal"]) for e in exercises} != expected or len(exercises) != 9:
        errors.append("Exercise coverage must be exactly three brand types × three goals")
    for exercise in exercises:
        if not exercise.get("briefFacts") or not exercise.get("directions") or not exercise.get("reviewCriteria"):
            errors.append(f"{exercise['id']}: missing facts, direction or review criteria")
        if set(exercise.get("frameworkIds", [])) - set(fids):
            errors.append(f"{exercise['id']}: unknown framework")
        if exercise.get("simulation") is not True or exercise.get("commercialResult") != "not-tested":
            errors.append(f"{exercise['id']}: fictional exercise presented as a measured result")
        if not exercise.get("requiredEvidence") or not exercise.get("rejectedDirection"):
            errors.append(f"{exercise['id']}: missing evidence requirements or rejected alternative")
        directions = exercise.get("directions", [])
        if len(directions) < 2 or len({d.get("name") for d in directions}) != len(directions):
            errors.append(f"{exercise['id']}: directions must be distinct")
    result = {
        "schemaVersion": "clicko.creative-research-coverage.v1",
        "documentIntegrity": "passed" if not errors else "failed",
        "selectedCases": len(cases),
        "caseStatuses": dict(sorted(Counter(c["status"] for c in cases).items())),
        "fullyReviewedAudiovisualCases": audiovisual_complete,
        "casesRequiringAudiovisualReview": audiovisual_required,
        "mediaCoverageGaps": gaps,
        "caseCountsByAuthor": dict(sorted(authors.items())),
        "discoveredCandidatesByAuthor": discovered,
        "frameworkCount": len(frameworks),
        "exerciseCount": len(exercises),
        "totalDiscoveredCandidates": sum(discovered.values()),
        "humanReview": "not-attested",
        "prototypeGate": "review-required",
        "runtimeImplementation": "not-part-of-this-research-delivery",
        "errors": errors,
        "inputsSha256": {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
                         for name in ("candidates.json", "cases.json", "frameworks.json", "exercises.json")},
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    report = validate(args.root)
    if args.write_report:
        (args.root / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not report["errors"] else 1)
