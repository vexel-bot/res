from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

CREATORS = (
    "paulo-ia",
    "mep-io",
    "gaveta",
    "cleo-abram",
    "johnny-harris",
    "marques-brownlee",
    "colin-and-samir",
    "mrbeast",
    "ryan-trahan",
    "zach-king",
    "daniel-schiffer",
    "sam-kolder",
    "dan-mace",
    "ali-abdaal",
    "james-jani",
    "magnatesmedia",
    "fern",
    "vox",
    "kurzgesagt",
    "corridor-digital",
)
WRITERS = (
    "jk-rowling-harry-potter",
    "duffer-brothers",
    "vince-gilligan-peter-gould",
    "phoebe-waller-bridge",
    "aaron-sorkin",
    "charlie-kaufman",
    "tony-gilroy",
    "jordan-peele",
    "greta-gerwig",
    "hayao-miyazaki",
    "billy-wilder-ia-diamond",
    "akira-kurosawa-shinobu-hashimoto",
    "nora-ephron",
    "paddy-chayefsky",
    "william-goldman",
    "paul-schrader",
    "spike-lee",
    "bong-joon-ho-han-jin-won",
    "celine-sciamma",
    "park-chan-wook-jeong-seo-kyeong",
    "guillermo-del-toro",
    "alfonso-cuaron",
    "asghar-farhadi",
    "alice-birch",
    "mike-leigh",
    "shonda-rhimes",
    "david-simon-ed-burns",
    "john-august-craig-mazin",
    "michael-arndt",
    "armando-iannucci-jesse-armstrong",
)
DIRECTORS = (
    "christopher-nolan",
    "steven-spielberg",
    "denis-villeneuve",
    "david-fincher",
    "bong-joon-ho",
    "hayao-miyazaki",
    "jordan-peele",
    "greta-gerwig",
    "alfonso-cuaron",
    "edgar-wright",
)
EDITORS = (
    "walter-murch",
    "thelma-schoonmaker",
    "lee-smith",
    "jennifer-lame",
    "kirk-baxter",
    "joe-walker",
    "margaret-sixel",
    "eddie-hamilton",
    "tom-cross",
    "rotating-contemporary-seat",
)
CRAFT = {
    "cinematography": (
        "roger-deakins",
        "hoyte-van-hoytema",
        "greig-fraser",
        "bradford-young",
        "emmanuel-lubezki",
        "rachel-morrison",
        "linus-sandgren",
        "jarin-blaschke",
        "ed-lachman",
        "lol-crawley",
    ),
    "production_design": (
        "nathan-crowley",
        "stuart-craig",
        "sarah-greenwood",
        "rick-carter",
        "patrice-vermette",
        "hannah-beachler",
        "eugenio-caballero",
        "syd-mead",
        "rick-heinrichs",
        "dante-ferretti",
    ),
    "motion_vfx": (
        "saul-bass",
        "kyle-cooper",
        "ash-thorp",
        "gmunk",
        "ordinary-folk",
        "buck",
        "andrew-kramer",
        "ian-hubert",
        "paul-trillo",
        "corridor-digital",
    ),
    "sound_music": (
        "ben-burtt",
        "randy-thom",
        "gary-rydstrom",
        "ren-klyce",
        "richard-king",
        "hans-zimmer",
        "ludwig-goransson",
        "hildur-gudnadottir",
        "nicholas-britell",
        "trent-reznor-atticus-ross",
    ),
}


def rows() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    creator_slots = (
        ["relative_highlight"] * 4 + ["canonical"] * 3 + ["language_variant"] * 2 + ["instructional_failure"]
    )
    cinema_slots = ["canonical"] * 4 + ["contrast"] * 3 + ["atypical"] * 2 + ["instructional_limitation"]
    for subject in CREATORS:
        for index, slot in enumerate(creator_slots, 1):
            result.append(
                {
                    "unit_id": f"creator-{subject}-{index:02d}",
                    "cohort": "creators",
                    "subject": subject,
                    "selection_slot": slot,
                }
            )
    for subject in WRITERS:
        for index, slot in enumerate(cinema_slots, 1):
            result.append(
                {
                    "unit_id": f"writer-{subject}-{index:02d}",
                    "cohort": "screenwriting",
                    "subject": subject,
                    "selection_slot": slot,
                }
            )
    for subject in DIRECTORS:
        for index, slot in enumerate(cinema_slots, 1):
            result.append(
                {
                    "unit_id": f"director-{subject}-{index:02d}",
                    "cohort": "direction",
                    "subject": subject,
                    "selection_slot": slot,
                }
            )
    for subject in EDITORS:
        for index, slot in enumerate(cinema_slots, 1):
            result.append(
                {
                    "unit_id": f"editor-{subject}-{index:02d}",
                    "cohort": "editing",
                    "subject": subject,
                    "selection_slot": slot,
                }
            )
    for cohort, subjects in CRAFT.items():
        for subject in subjects:
            for index in range(1, 6):
                result.append(
                    {
                        "unit_id": f"{cohort}-{subject}-{index:02d}",
                        "cohort": cohort,
                        "subject": subject,
                        "selection_slot": "craft_case",
                    }
                )
    for item in result:
        item.update(
            {
                "source_url": "",
                "work_or_sequence": "",
                "status": "blocked_by_r1_human_approval",
                "analysis_path": "",
                "shots_path": "",
                "primary_reviewer": "",
                "second_review_required": False,
                "notes": "Selection candidate has not been researched or annotated; this row is not evidence.",
            }
        )
    # Deterministic 10% second-review sample. It becomes actionable only after source selection.
    for index, item in enumerate(result):
        item["second_review_required"] = index % 10 == 0
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    data = rows()
    if len(data) != 900:
        raise RuntimeError(f"Expected 900 planned corpus units, got {len(data)}")
    args.output_root.mkdir(parents=True, exist_ok=True)
    fields = list(data[0])
    with (args.output_root / "corpus-manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)
    counts: dict[str, int] = {}
    for item in data:
        counts[item["cohort"]] = counts.get(item["cohort"], 0) + 1
    (args.output_root / "coverage.json").write_text(
        json.dumps(
            {
                "schema_version": "studio.corpus-coverage.v1",
                "target": 900,
                "planned": len(data),
                "annotated_in_main_corpus": 0,
                "r1_calibration_units": 12,
                "human_approved": 0,
                "second_review_required": sum(bool(item["second_review_required"]) for item in data),
                "counts": counts,
                "complete": False,
                "blocker": "R1 human review and taxonomy approval required before selection and annotation",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
