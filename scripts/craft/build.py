"""Build pinned real Craft adapters and package the server runtime.

Usage: python scripts/craft/build.py [--engine photocraft|filmcraft|effectcraft]
       python scripts/craft/build.py --wasm
       python scripts/craft/build.py --references
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = {"photocraft": "photo", "filmcraft": "film", "effectcraft": "effect"}
BINDGEN_VERSION = "0.2.129"


def bindgen(*, host=False):
    """Fetch the version matching the locked Rust ABI and verify its release digest."""
    platform = (
        "x86_64-pc-windows-msvc"
        if host and os.name == "nt"
        else "x86_64-unknown-linux-musl"
    )
    name = f"wasm-bindgen-{BINDGEN_VERSION}-{platform}"
    tools = ROOT / ".codex-runtime/craft/tools"
    executable = (
        tools
        / name
        / ("wasm-bindgen.exe" if platform.endswith("windows-msvc") else "wasm-bindgen")
    )
    if not executable.is_file():
        tools.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/wasm-bindgen/wasm-bindgen/releases/download/{BINDGEN_VERSION}/{name}.tar.gz"
        archive = tools / f"{name}.tar.gz"
        with urllib.request.urlopen(url + ".sha256sum") as response:
            expected = response.read().decode("utf-8").split()[0]
        urllib.request.urlretrieve(url, archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ValueError("wasm-bindgen release checksum mismatch")
        with tarfile.open(archive) as package:
            package.extractall(tools, filter="data")
    return (
        str(executable)
        if host
        else "/workspace/" + executable.relative_to(ROOT).as_posix()
    )


def command(*args):
    subprocess.run(list(args), cwd=ROOT, check=True)


def package_browser(engine, public, raw=None):
    """Refresh attribution/provenance without recompiling already generated WASM."""
    required = [
        public / f"clicko_{engine}_adapter{suffix}" for suffix in (".js", "_bg.wasm")
    ]
    if not all(file.is_file() and file.stat().st_size for file in required):
        raise ValueError(f"Missing generated browser bundle for {engine}")
    source = ROOT / "third_party/craft" / engine
    for filename in ("LICENSE-MIT", "LICENSE-APACHE", "NOTICE", "ATTRIBUTION.md"):
        if (source / filename).is_file():
            shutil.copyfile(source / filename, public / filename)
    for dependency in (ROOT / "third_party/craft").iterdir():
        for file in dependency.rglob("*"):
            if not file.is_file() or "target" in file.parts or "brand" in file.parts:
                continue
            name = file.name.lower()
            if (
                name.startswith(("license", "copying", "ofl"))
                or name in {"notice", "attribution.md"}
                or name.endswith(".attribution")
            ):
                destination = (
                    public / "licenses" / dependency.name / file.relative_to(dependency)
                )
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file, destination)
    old_path = public / "manifest.json"
    previous = (
        json.loads(old_path.read_text(encoding="utf-8")) if old_path.is_file() else {}
    )
    manifest = {
        "schemaVersion": "clicko.craft-browser.v1",
        "engine": engine,
        "upstreamRevision": next(
            item["commit"]
            for item in json.loads(
                (ROOT / "workers/craft/sources.lock.json").read_text(encoding="utf-8")
            )["sources"]
            if item["name"] == engine
        ),
        "wasmBindgenVersion": BINDGEN_VERSION,
        "rawWasmSha256": hashlib.sha256(raw.read_bytes()).hexdigest()
        if raw and raw.is_file()
        else previous.get("rawWasmSha256"),
        "files": {
            file.relative_to(public).as_posix(): hashlib.sha256(
                file.read_bytes()
            ).hexdigest()
            for file in public.rglob("*")
            if file.is_file() and file != old_path
        },
    }
    old_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


@contextmanager
def build_lock():
    path = ROOT / ".codex-runtime/craft/build.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            waiting = False
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if not waiting:
                        print(
                            "Waiting for the other Craft build to finish (bounded memory).",
                            flush=True,
                        )
                        waiting = True
                    time.sleep(1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=ADAPTERS)
    parser.add_argument("--wasm", action="store_true")
    parser.add_argument("--references", action="store_true")
    parser.add_argument(
        "--browser-package-only",
        action="store_true",
        help="Refresh provenance and licenses in existing browser bundles",
    )
    parser.add_argument(
        "--bindgen-only",
        action="store_true",
        help="Package already compiled WASM artifacts",
    )
    parser.add_argument(
        "--package-only",
        action="store_true",
        help="Package previously built native binaries",
    )
    args = parser.parse_args()
    if args.browser_package_only:
        if args.bindgen_only or args.package_only or args.references:
            parser.error(
                "--browser-package-only cannot combine with native/compile packaging"
            )
        for engine in [args.engine] if args.engine else list(ADAPTERS):
            package_browser(engine, ROOT / "public/craft" / engine)
        return
    if args.bindgen_only and args.package_only:
        parser.error("--bindgen-only and --package-only are mutually exclusive")
    if not shutil.which("docker") and not (args.bindgen_only and os.name == "nt"):
        parser.error("Docker with a Linux engine is required for Craft builds. No substitute renderer will be used.")
    args.wasm = args.wasm or args.bindgen_only
    if not args.package_only and not args.bindgen_only:
        command(
            "docker",
            "build",
            "-f",
            "workers/craft/Dockerfile.builder",
            "-t",
            "clicko-craft-builder:local",
            "workers/craft",
        )
        command("docker", "volume", "create", "clicko-craft-cargo")
        command("docker", "volume", "create", "clicko-craft-target")
    output = ROOT / ".codex-runtime/craft/bin"
    output.mkdir(parents=True, exist_ok=True)
    engines = (
        [] if args.package_only else ([args.engine] if args.engine else list(ADAPTERS))
    )
    for engine in engines:
        manifest = f"workers/craft/adapters/{ADAPTERS[engine]}/Cargo.toml"
        cargo = ["cargo", "build", "--manifest-path", manifest, "--release", "--locked"]
        if args.wasm:
            cargo += ["--target", "wasm32-unknown-unknown", "--lib"]
            if engine == "effectcraft":
                # The embedded expression VM overwhelms small Docker VMs at O3.
                # Keep all features; bound LLVM memory for this browser dependency.
                cargo += ["--config", "profile.release.package.boa_engine.opt-level=1"]
        run = [
            "docker",
            "run",
            "--rm",
            "--memory=2g",
            "--memory-swap=3g",
            "--cpus=2",
            "--mount",
            f"type=bind,source={ROOT},target=/workspace",
            "--mount",
            "type=volume,source=clicko-craft-cargo,target=/cargo",
            "--mount",
            "type=volume,source=clicko-craft-target,target=/target",
            "-e",
            "CRAFT_FONTS_DIR=/workspace/third_party/craft/craft-fonts",
            "-e",
            "CARGO_BUILD_JOBS=1",
            "-e",
            "CARGO_PROFILE_RELEASE_LTO=false",
            "-e",
            "CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16",
            "-e",
            f"CARGO_TARGET_DIR=/target/{ADAPTERS[engine] if engine != 'photocraft' else ''}",
            "clicko-craft-builder:local",
        ]
        if not args.bindgen_only:
            command(*run, *cargo)
        target = (
            f"/target/{ADAPTERS[engine]}/" if engine != "photocraft" else "/target/"
        )
        if args.wasm:
            public = ROOT / "public/craft" / engine
            public.mkdir(parents=True, exist_ok=True)
            raw = f"{target}wasm32-unknown-unknown/release/clicko_{engine}_adapter.wasm"
            if os.name == "nt":
                # Bindgen's IR uses host paging instead of sharing Docker's RAM.
                native_raw = ROOT / f".codex-runtime/craft/{engine}-unbound.wasm"
                if not (args.bindgen_only and native_raw.is_file()):
                    command(
                        *run,
                        "cp",
                        raw,
                        "/workspace/" + native_raw.relative_to(ROOT).as_posix(),
                    )
                prefix, executable, input_path, out_path = (
                    [],
                    bindgen(host=True),
                    str(native_raw),
                    str(public),
                )
            else:
                prefix, executable, input_path, out_path = (
                    run,
                    bindgen(),
                    raw,
                    f"/workspace/public/craft/{engine}",
                )
            command(
                *prefix,
                executable,
                "--target",
                "web",
                "--no-demangle",
                "--remove-name-section",
                "--out-name",
                f"clicko_{engine}_adapter",
                "--out-dir",
                out_path,
                input_path,
            )
            package_browser(engine, public, native_raw if os.name == "nt" else None)
        else:
            name = f"clicko-{engine}-adapter"
            command(
                *run,
                "cp",
                f"{target}release/{name}",
                f"/workspace/.codex-runtime/craft/bin/{name}",
            )
        if args.references:
            command(
                *run,
                "cargo",
                "build",
                "--manifest-path",
                f"third_party/craft/{engine}/Cargo.toml",
                "--release",
                "--locked",
                "-p",
                f"{engine}-cli",
            )
    if not args.wasm and all(
        (output / f"clicko-{engine}-adapter").is_file() for engine in ADAPTERS
    ):
        license_output = ROOT / ".codex-runtime/craft/licenses"
        for source in (ROOT / "third_party/craft").iterdir():
            for file in source.rglob("*"):
                if (
                    not file.is_file()
                    or "target" in file.parts
                    or "brand" in file.parts
                ):
                    continue
                name = file.name.lower()
                if (
                    name.startswith(("license", "copying", "ofl"))
                    or name in {"notice", "attribution.md"}
                    or name.endswith(".attribution")
                ):
                    destination = (
                        license_output / source.name / file.relative_to(source)
                    )
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(file, destination)
        lock = json.loads(
            (ROOT / "workers/craft/sources.lock.json").read_text(encoding="utf-8")
        )
        builds = {
            engine: {
                "upstreamRevision": next(
                    source["commit"]
                    for source in lock["sources"]
                    if source["name"] == engine
                ),
                "sha256": hashlib.sha256(
                    (output / f"clicko-{engine}-adapter").read_bytes()
                ).hexdigest(),
            }
            for engine in ADAPTERS
        }
        (ROOT / ".codex-runtime/craft/runtime-manifest.json").write_text(
            json.dumps(
                {"schemaVersion": "clicko.craft-runtime.v1", "engines": builds},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        command(
            "docker",
            "build",
            "-f",
            "workers/craft/Dockerfile.runtime",
            "-t",
            "clicko-craft-runtime:local",
            ".",
        )


if __name__ == "__main__":
    with build_lock():
        main()
