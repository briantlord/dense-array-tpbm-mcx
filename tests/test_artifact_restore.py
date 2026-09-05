import pytest

from mcx_project.artifact_restore import verify_or_restore
from mcx_project.hashing import sha256_file
from mcx_project.validation import InputValidationError


def test_restore_verifies_bytes_and_never_overwrites(tmp_path):
    source = tmp_path / "mirror"
    destination = tmp_path / "checkout"
    source.mkdir(); destination.mkdir()
    path = source / "field.bin"
    path.write_bytes(bytes(range(256)))
    records = [{"path": "field.bin", "sha256": sha256_file(path)}]
    assert verify_or_restore(destination, records)["missing"] == 1
    assert verify_or_restore(destination, records, source)["restored"] == 1
    assert verify_or_restore(destination, records)["verified"] == 1
    (destination / "field.bin").write_bytes(b"local evidence")
    with pytest.raises(InputValidationError, match="not overwritten"):
        verify_or_restore(destination, records, source)
    assert (destination / "field.bin").read_bytes() == b"local evidence"


def test_restore_rejects_corrupt_mirror(tmp_path):
    source = tmp_path / "mirror"
    source.mkdir()
    (source / "field.bin").write_bytes(b"bad")
    with pytest.raises(InputValidationError, match="checksum mismatch"):
        verify_or_restore(tmp_path / "checkout", [{"path": "field.bin", "sha256": "0"*64}], source)
