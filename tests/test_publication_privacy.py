"""Regression checks for accidental disclosure at publication boundaries."""

import importlib.util
from pathlib import Path
import hashlib

spec = importlib.util.spec_from_file_location("publication", Path(__file__).parents[1] / "scripts/check_publication.py")
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


def policy():
    return {"protected_token_sha256": [], "approved_contact_email_sha256": [], "approved_binary_sha256": {}}


def test_personal_paths_in_nested_json_and_traceback():
    value = "C:" + "\\" * 4 + "Users" + "\\" * 4 + "example" + "\\" * 4 + "project"
    assert "personal absolute path" in publication.check_text(value.encode(), policy())
    value = "/" + "Users/" + "example/project"
    assert "personal absolute path" in publication.check_text(value.encode(), policy())
    assert not publication.check_text(b".local/bin/simulator", policy())


def test_email_requires_explicit_approval_or_noreply():
    address = b"person" + b"@" + b"example.invalid"
    assert publication.check_text(address, policy())
    allowed = policy()
    allowed["approved_contact_email_sha256"] = [hashlib.sha256(address).hexdigest()]
    assert not publication.check_text(address, allowed)
    assert not publication.check_text(b"account" + b"@users.noreply.github.com", policy())


def test_credentials_rejected_without_disclosing_values():
    secret = b"gh" + b"p_" + b"X" * 36
    findings = publication.check_text(secret, policy())
    assert "service token" in findings
    assert secret.decode() not in str(findings)
    assert publication.check_text(b"pass" + b"word = '" + b"sample-value'", policy())


def test_device_identifier_in_path_or_text_is_blocked():
    protected = b"exampledevice"
    rules = policy()
    rules["protected_token_sha256"] = [hashlib.sha256(protected).hexdigest()]
    assert publication.check_file(protected.decode()+"/notes.md", b"", rules)
    assert publication.check_text(protected.upper(), rules)


def test_disguised_pdf_and_unreviewed_zip_are_blocked():
    assert publication.check_file("notes.txt", b"%PDF-1.7 example", policy())
    assert publication.check_file("notes.dat", b"PK\x03\x04example", policy())


def test_binary_approval_is_bound_to_path_and_content():
    data = b"\x00reviewed-asset"
    rules = policy()
    rules["approved_binary_sha256"]["plot.png"] = hashlib.sha256(data).hexdigest()
    assert not publication.check_file("plot.png", data, rules)
    assert publication.check_file("photo.png", data, rules)
    assert publication.check_file("plot.png", data+b"changed", rules)


def test_private_working_files_are_blocked():
    assert publication.check_file("tmp/notes.txt", b"text", policy())
    assert publication.check_file(".env", b"text", policy())
    assert publication.check_file("paper.pdf", b"text", policy())
