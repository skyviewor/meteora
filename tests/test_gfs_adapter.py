import io
import subprocess

import httpx
import pytest

from aero.adapters.gfs_adapter import (
    GFSAdapter,
    parse_gfs_idx,
    select_gfs_entries,
    summarize_gfs_inventory,
)

IDX_TEXT = """1:0:d=2026060400:PRMSL:mean sea level:anl:
2:998971:d=2026060400:TMP:2 m above ground:anl:
3:1101952:d=2026060400:TMP:500 mb:anl:
4:1313579:d=2026060400:UGRD:500 mb:anl:
5:1513579:d=2026060400:APCP:surface:0-1 hour acc fcst:
"""


def test_parse_gfs_idx_computes_byte_ranges():
    entries = parse_gfs_idx(IDX_TEXT)

    assert len(entries) == 5
    assert entries[0].start_byte == 0
    assert entries[0].end_byte == 998970
    assert entries[1].range_header == "bytes=998971-1101951"
    assert entries[3].start_byte == 1313579
    assert entries[3].end_byte == 1513578
    assert entries[-1].start_byte == 1513579
    assert entries[-1].end_byte is None
    assert entries[-1].range_header == "bytes=1513579-"


def test_select_gfs_entries_matches_variable_and_level():
    entries = parse_gfs_idx(IDX_TEXT)

    selected, missing = select_gfs_entries(entries, ["TMP", "RH"], ["500 mb"])

    assert [(e.variable, e.level) for e in selected] == [("TMP", "500 mb")]
    assert missing == [{"variable": "RH", "level": "500 mb"}]


def test_summarize_gfs_inventory_filters_variable():
    entries = parse_gfs_idx(IDX_TEXT)

    inventory = summarize_gfs_inventory(entries, ["APCP"])

    assert inventory == [
        {
            "variable": "APCP",
            "level": "surface",
            "forecast": "0-1 hour acc fcst",
            "message_count": 1,
            "byte_count": 0,
            "examples": ["5:1513579:d=2026060400:APCP:surface:0-1 hour acc fcst:"],
        }
    ]


def test_download_ranges_uses_http_range_headers(tmp_path, monkeypatch):
    entries = parse_gfs_idx(IDX_TEXT)[:2]
    dest = tmp_path / "subset.grib2"
    seen_ranges = []

    class FakeStream:
        def __init__(self, headers):
            self.headers = headers
            self.status_code = 206

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def iter_bytes(self, chunk_size):
            yield self.headers["Range"].encode()

        def raise_for_status(self):
            raise AssertionError("unexpected status error")

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def stream(self, method, url, headers):
            assert method == "GET"
            assert url == "https://example.com/gfs"
            seen_ranges.append(headers["Range"])
            return FakeStream(headers)

    monkeypatch.setattr("aero.adapters.gfs_adapter.httpx.Client", FakeClient)

    size = GFSAdapter._download_ranges("https://example.com/gfs", entries, dest, 100)

    assert seen_ranges == ["bytes=0-998970", "bytes=998971-1101951"]
    assert size == dest.stat().st_size
    assert dest.read_bytes() == b"bytes=0-998970bytes=998971-1101951"


def test_fetch_text_uses_controlled_fallback_for_tls_error(monkeypatch):
    def fail_httpx(url):
        raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")

    seen = []

    def fake_curl(url):
        seen.append(url)
        return IDX_TEXT

    monkeypatch.setattr(GFSAdapter, "_fetch_text_httpx", staticmethod(fail_httpx))
    monkeypatch.setattr(GFSAdapter, "_fetch_text_curl", staticmethod(fake_curl))

    assert GFSAdapter._fetch_text("https://example.com/gfs.idx") == IDX_TEXT
    assert seen == ["https://example.com/gfs.idx"]


def test_fetch_text_does_not_fallback_for_non_tls_transport_error(monkeypatch):
    def fail_httpx(url):
        raise httpx.ConnectError("connection refused")

    def unexpected_curl(url):
        raise AssertionError("non-TLS errors must not use the curl fallback")

    monkeypatch.setattr(GFSAdapter, "_fetch_text_httpx", staticmethod(fail_httpx))
    monkeypatch.setattr(GFSAdapter, "_fetch_text_curl", staticmethod(unexpected_curl))

    with pytest.raises(httpx.ConnectError, match="connection refused"):
        GFSAdapter._fetch_text("https://example.com/gfs.idx")


def test_curl_range_fallback_preserves_idx_ranges(tmp_path, monkeypatch):
    entries = parse_gfs_idx(IDX_TEXT)[:2]
    dest = tmp_path / "subset.grib2"
    commands = []
    payloads = iter([b"first", b"second"])

    class FakeProcess:
        def __init__(self, command):
            commands.append(command)
            self.stdout = io.BytesIO(next(payloads))
            self.stderr = io.BytesIO()
            self.returncode = 0

        def communicate(self):
            return b"", self.stderr.read()

        def terminate(self):
            self.returncode = -15

    monkeypatch.setattr(
        "aero.adapters.gfs_adapter._curl_executable",
        lambda: "/usr/bin/curl",
    )
    monkeypatch.setattr(
        "aero.adapters.gfs_adapter.subprocess.Popen",
        lambda command, **kwargs: FakeProcess(command),
    )

    size = GFSAdapter._download_ranges_curl(
        "https://example.com/gfs",
        entries,
        dest,
        total_bytes=11,
    )

    assert size == 11
    assert dest.read_bytes() == b"firstsecond"
    assert [command[command.index("--range") + 1] for command in commands] == [
        "0-998970",
        "998971-1101951",
    ]


def test_fetch_text_curl_uses_fail_and_retry(monkeypatch):
    seen = []

    def fake_run(command, **kwargs):
        seen.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=IDX_TEXT.encode())

    monkeypatch.setattr(
        "aero.adapters.gfs_adapter._curl_executable",
        lambda: "/usr/bin/curl",
    )
    monkeypatch.setattr("aero.adapters.gfs_adapter.subprocess.run", fake_run)

    assert GFSAdapter._fetch_text_curl("https://example.com/gfs.idx") == IDX_TEXT
    command, kwargs = seen[0]
    assert command[0] == "/usr/bin/curl"
    assert "--fail" in command
    assert command[command.index("--retry") + 1] == "2"
    assert kwargs == {"check": True, "capture_output": True}


@pytest.mark.asyncio
async def test_download_one_selects_idx_messages(tmp_path, monkeypatch):
    def fake_fetch_text(url):
        assert url.endswith(".idx")
        return IDX_TEXT

    def fake_download_ranges(url, entries, dest, total_bytes, on_progress=None):
        dest.write_bytes(b"GRIB")
        return 4

    monkeypatch.setattr(GFSAdapter, "_fetch_text", staticmethod(fake_fetch_text))
    monkeypatch.setattr(GFSAdapter, "_download_ranges", staticmethod(fake_download_ranges))

    adapter = GFSAdapter(base_url="https://example.com")
    result = await adapter.download_one(
        date="2026-06-04",
        cycle="00",
        forecast_hour=0,
        variables=["TMP"],
        levels=["500 mb"],
        dest_dir=tmp_path,
    )

    assert result.file_path.read_bytes() == b"GRIB"
    assert result.selected_entries[0].variable == "TMP"
    assert result.selected_entries[0].level == "500 mb"
    assert result.missing == []
