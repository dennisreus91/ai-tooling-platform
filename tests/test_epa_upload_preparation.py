from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from gemini_service import _extract_xml_from_epa, _prepare_file_for_upload


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_extract_xml_from_epa_selects_valid_xml(tmp_path: Path):
    epa_path = tmp_path / "sample.epa"
    _write_zip(
        epa_path,
        {
            "metadata/readme.txt": b"not xml",
            "woning/project_data.xml": b"<root><woning><bouwjaar>1992</bouwjaar></woning></root>",
        },
    )

    extracted_path = _extract_xml_from_epa(str(epa_path))
    extracted_content = Path(extracted_path).read_text(encoding="utf-8")

    assert "<bouwjaar>1992</bouwjaar>" in extracted_content

    Path(extracted_path).unlink(missing_ok=True)


def test_extract_xml_from_epa_raises_when_no_xml(tmp_path: Path):
    epa_path = tmp_path / "sample.epa"
    _write_zip(epa_path, {"data.bin": b"\x00\x01\x02"})

    with pytest.raises(ValueError, match="epa_xml_missing"):
        _extract_xml_from_epa(str(epa_path))


def test_prepare_file_for_upload_epa_returns_xml_path_and_mime(tmp_path: Path):
    epa_path = tmp_path / "sample.epa"
    _write_zip(epa_path, {"foo.xml": b"<project><id>123</id></project>"})

    prepared_path, mime_type, cleanup_paths = _prepare_file_for_upload(str(epa_path))

    assert prepared_path.endswith(".xml")
    assert mime_type == "text/xml"
    assert cleanup_paths == [prepared_path]
    assert Path(prepared_path).exists()

    for path in cleanup_paths:
        Path(path).unlink(missing_ok=True)
