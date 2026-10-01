from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path
from typing import Any

_INDEX_MEDIA_TYPES = {
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
}


def _fail(reason: str) -> None:
    raise SystemExit(reason)


def _extract_safe(archive: Path, target: Path) -> None:
    with tarfile.open(archive, mode="r:*") as tar:
        members = tar.getmembers()
        for member in members:
            name = Path(member.name)
            if name.is_absolute() or ".." in name.parts:
                _fail("oci_tar_path_traversal")
            destination = (target / name).resolve()
            if not destination.is_relative_to(target.resolve()):
                _fail("oci_tar_path_traversal")
        tar.extractall(target, members=members)


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        _fail(f"oci_json_unreadable:{path.name}")
        raise AssertionError from error
    if not isinstance(value, dict):
        _fail(f"oci_json_object_required:{path.name}")
    return value


def _blob(root: Path, digest: str) -> bytes:
    if not digest.startswith("sha256:"):
        _fail("oci_digest_algorithm_unsupported")
    value = digest.removeprefix("sha256:")
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        _fail("oci_digest_invalid")
    path = root / "blobs" / "sha256" / value
    try:
        payload = path.read_bytes()
    except OSError as error:
        _fail(f"oci_blob_missing:{digest}")
        raise AssertionError from error
    if hashlib.sha256(payload).hexdigest() != value:
        _fail(f"oci_blob_digest_mismatch:{digest}")
    return payload


def _manifest(root: Path, descriptor: dict[str, Any]) -> dict[str, Any]:
    digest = descriptor.get("digest")
    if not isinstance(digest, str):
        _fail("oci_manifest_digest_missing")
    try:
        value = json.loads(_blob(root, digest).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail("oci_manifest_invalid_json")
        raise AssertionError from error
    if not isinstance(value, dict):
        _fail("oci_manifest_object_required")
    return value


def _flatten_descriptors(
    root: Path,
    descriptors: list[Any],
    *,
    visited_indexes: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Resolve OCI image indexes while retaining manifest descriptors.

    BuildKit's OCI exporter may put a platform index below the layout's root
    index. Digest verification still happens through ``_manifest``/``_blob``;
    cycles and malformed nested indexes fail closed.
    """
    visited = set() if visited_indexes is None else visited_indexes
    flattened: list[dict[str, Any]] = []
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            _fail("oci_descriptor_invalid")
        media_type = descriptor.get("mediaType")
        if media_type not in _INDEX_MEDIA_TYPES:
            flattened.append(descriptor)
            continue
        digest = descriptor.get("digest")
        if not isinstance(digest, str):
            _fail("oci_index_digest_missing")
        if digest in visited:
            _fail("oci_index_cycle")
        visited.add(digest)
        nested_index = _manifest(root, descriptor)
        nested_descriptors = nested_index.get("manifests")
        if not isinstance(nested_descriptors, list) or not nested_descriptors:
            _fail("oci_nested_index_manifests_missing")
        flattened.extend(
            _flatten_descriptors(
                root,
                nested_descriptors,
                visited_indexes=visited,
            )
        )
    return flattened


def _attestation_statement(
    payload: bytes,
    *,
    image_manifest_digest: str,
    attestation_reference_digest: str | None,
) -> tuple[str, dict[str, Any], str]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail("oci_attestation_statement_invalid")
        raise AssertionError from error
    if not isinstance(value, dict):
        _fail("oci_attestation_statement_object_required")
    predicate_type = value.get("predicateType")
    if not isinstance(predicate_type, str) or not predicate_type:
        _fail("oci_attestation_predicate_type_missing")
    subjects = value.get("subject")
    expected = image_manifest_digest.removeprefix("sha256:")
    if not isinstance(subjects, list):
        _fail("oci_attestation_subject_list_missing")
    subject_bound = any(
        isinstance(subject, dict)
        and isinstance(subject.get("digest"), dict)
        and subject["digest"].get("sha256") == expected
        for subject in subjects
    )
    reference_bound = attestation_reference_digest == image_manifest_digest
    if subjects and not subject_bound:
        _fail("oci_attestation_subject_binding_missing")
    if not subject_bound and not (not subjects and reference_bound):
        _fail("oci_attestation_binding_missing")
    predicate = value.get("predicate")
    if not isinstance(predicate, dict):
        _fail("oci_attestation_predicate_object_required")
    binding_method = "statement_subject" if subject_bound else "oci_reference_digest"
    return predicate_type, predicate, binding_method


def verify(
    archive: Path,
    *,
    expected_title: str,
    expected_provider_label: str = "none",
    expected_architecture: str = "amd64",
    expected_os: str = "linux",
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="clicko-oci-") as temporary:
        root = Path(temporary)
        _extract_safe(archive, root)
        layout = _json(root / "oci-layout")
        if layout.get("imageLayoutVersion") != "1.0.0":
            _fail("oci_layout_version_invalid")
        index = _json(root / "index.json")
        root_descriptors = index.get("manifests")
        if not isinstance(root_descriptors, list) or not root_descriptors:
            _fail("oci_index_manifests_missing")
        descriptors = _flatten_descriptors(root, root_descriptors)

        image_descriptors = [
            item
            for item in descriptors
            if isinstance(item, dict)
            and item.get("mediaType") in {
                "application/vnd.oci.image.manifest.v1+json",
                "application/vnd.docker.distribution.manifest.v2+json",
            }
            and isinstance(item.get("platform"), dict)
            and item["platform"].get("architecture") == expected_architecture
            and item["platform"].get("os") == expected_os
        ]
        if len(image_descriptors) != 1:
            _fail("oci_linux_amd64_image_manifest_count_invalid")
        image_descriptor = image_descriptors[0]
        image_manifest_digest = image_descriptor["digest"]
        image = _manifest(root, image_descriptor)
        config_descriptor = image.get("config")
        if not isinstance(config_descriptor, dict) or not isinstance(config_descriptor.get("digest"), str):
            _fail("oci_image_config_missing")
        config = json.loads(_blob(root, config_descriptor["digest"]).decode("utf-8"))
        if not isinstance(config, dict):
            _fail("oci_image_config_invalid")
        labels = config.get("config", {}).get("Labels", {})
        if not isinstance(labels, dict):
            _fail("oci_image_labels_missing")
        if labels.get("org.opencontainers.image.title") != expected_title:
            _fail("oci_image_title_mismatch")
        if labels.get("io.clicko.providers") != expected_provider_label:
            _fail("oci_provider_label_mismatch")

        attestation_descriptors = [
            item
            for item in descriptors
            if isinstance(item, dict)
            and isinstance(item.get("annotations"), dict)
            and item["annotations"].get("vnd.docker.reference.type") == "attestation-manifest"
        ]
        if not attestation_descriptors:
            _fail("oci_attestation_missing")
        has_provenance = False
        has_sbom = False
        binding_methods: set[str] = set()
        for descriptor in attestation_descriptors:
            annotations = descriptor.get("annotations")
            if not isinstance(annotations, dict):
                _fail("oci_attestation_annotations_missing")
            reference_digest = annotations.get("vnd.docker.reference.digest")
            attestation = _manifest(root, descriptor)
            for layer in attestation.get("layers", []):
                if not isinstance(layer, dict) or not isinstance(layer.get("digest"), str):
                    _fail("oci_attestation_layer_invalid")
                media_type = str(layer.get("mediaType", "")).lower()
                if "in-toto" not in media_type or "json" not in media_type:
                    _fail("oci_attestation_media_type_invalid")
                payload = _blob(root, layer["digest"])
                predicate_type, predicate, binding_method = _attestation_statement(
                    payload,
                    image_manifest_digest=image_manifest_digest,
                    attestation_reference_digest=(
                        reference_digest if isinstance(reference_digest, str) else None
                    ),
                )
                binding_methods.add(binding_method)
                lowered = predicate_type.lower()
                has_provenance = has_provenance or lowered.startswith(
                    "https://slsa.dev/provenance/"
                )
                has_sbom = has_sbom or (
                    lowered in {
                        "https://spdx.dev/document",
                        "https://cyclonedx.org/bom",
                    }
                    and (
                        "spdxVersion" in predicate
                        or "bomFormat" in predicate
                    )
                )
        if not has_provenance:
            _fail("oci_provenance_attestation_missing")
        if not has_sbom:
            _fail("oci_sbom_attestation_missing")
        return {
            "architecture": expected_architecture,
            "attestationCount": len(attestation_descriptors),
            "attestationBindingMethods": sorted(binding_methods),
            "imageDigest": image_manifest_digest,
            "providerLabel": labels.get("io.clicko.providers"),
            "status": "preflight-oci-verified",
            "title": labels.get("org.opencontainers.image.title"),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an OCI preflight artifact without pushing or running it.")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--provider-label", default="none")
    args = parser.parse_args()
    result = verify(args.archive, expected_title=args.title, expected_provider_label=args.provider_label)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
