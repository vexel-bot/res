"""Compile a typed discovery variant; never import or render via hidden UI calls."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.providers.studios.alight_text_compiler import (
    TextReferenceParameters,
    compile_text_reference,
)  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    parameters = TextReferenceParameters.model_validate_json(
        args.parameters.read_text(encoding="utf-8")
    )
    xml, receipt = compile_text_reference(parameters)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "project.xml").write_bytes(xml)
    (args.output / "compilation-receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"outputSha256": receipt["outputSha256"], "renderQualification": False}
        )
    )


if __name__ == "__main__":
    main()
