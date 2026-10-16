"""Build the local XML receiver. Never downloads dependencies or installs an APK."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    tools, output = args.tools.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    android = next(tools.glob("*/android.jar"))
    aapt = next(tools.glob("*/aapt.exe"))
    d8 = next(tools.glob("*/lib/d8.jar"))
    signer = next(tools.glob("*/lib/apksigner.jar"))
    ecj = tools / "ecj-3.37.0.jar"
    java = str(args.java.resolve())

    def run(*command):
        subprocess.run([str(value) for value in command], check=True, timeout=60)

    classes, dex = output / "classes", output / "dex"
    classes.mkdir(exist_ok=True)
    dex.mkdir(exist_ok=True)
    run(
        java,
        "-jar",
        ecj,
        "-1.8",
        "-encoding",
        "UTF-8",
        "-proc:none",
        "-bootclasspath",
        android,
        "-d",
        classes,
        source / "ReceiveProjectActivity.java",
    )
    run(
        java,
        "-cp",
        d8,
        "com.android.tools.r8.D8",
        "--lib",
        android,
        "--min-api",
        "24",
        "--output",
        dex,
        *classes.rglob("*.class"),
    )
    unsigned = output / "receiver-unsigned.apk"
    run(
        aapt,
        "package",
        "-f",
        "-M",
        source / "AndroidManifest.xml",
        "-I",
        android,
        "-F",
        unsigned,
    )
    with zipfile.ZipFile(unsigned, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(dex / "classes.dex", "classes.dex")
    # Development identity only, in the ignored output directory; never a user key.
    keystore, password_file = (
        output / "development.p12",
        output / "development-key-password.txt",
    )
    if not keystore.exists():
        import secrets

        password = secrets.token_urlsafe(32).encode()
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name(
            [x509.NameAttribute(NameOID.COMMON_NAME, "res local discovery receiver")]
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .sign(key, hashes.SHA256())
        )
        keystore.write_bytes(
            pkcs12.serialize_key_and_certificates(
                b"res-discovery",
                key,
                certificate,
                None,
                serialization.BestAvailableEncryption(password),
            )
        )
        password_file.write_bytes(password)
    apk = output / "res-alight-xml-receiver.apk"
    run(
        java,
        "-jar",
        signer,
        "sign",
        "--ks",
        keystore,
        "--ks-type",
        "PKCS12",
        "--ks-pass",
        "file:" + str(password_file),
        "--out",
        apk,
        unsigned,
    )
    run(java, "-jar", signer, "verify", "--verbose", apk)
    (output / "build-receipt.json").write_text(
        json.dumps(
            {
                "kind": "alight.xml_receiver_build.v1",
                "apk": apk.name,
                "sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
                "sourceHashes": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in source.iterdir()
                    if p.is_file()
                },
                "renderQualification": False,
                "permissions": [],
                "dependencies": json.loads(
                    (tools / "download-receipt.json").read_text()
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(apk)


if __name__ == "__main__":
    main()
