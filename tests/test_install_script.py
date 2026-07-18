from pathlib import Path


def test_install_script_uses_uv_and_never_initializes_a_project():
    script = Path("install.sh").read_text()

    download_base = (
        'AERO_DOWNLOAD_BASE="${AERO_DOWNLOAD_BASE:-https://aero.skyviewor.com/download}"'
    )
    assert download_base in script
    assert 'AERO_PACKAGE_URL="$AERO_DOWNLOAD_BASE/$ARCHIVE_FILE"' in script
    assert 'uv tool install --python 3.12 --force "$WHEEL_PATH"' in script
    assert "aero setup --yes" in script
    assert "aero init" not in script.split("安装完成")[0]
    assert "Miniconda" not in script
    assert "conda base" not in script
    assert "curl -fk" not in script
    assert "github.com" not in script.lower()
    assert "UV_DEFAULT_INDEX" in script


def test_install_script_has_fixed_archive_for_each_supported_platform():
    script = Path("install.sh").read_text()
    for archive in (
        "aero-macos-arm64.tar.gz",
        "aero-macos-x86_64.tar.gz",
        "aero-linux-x86_64.tar.gz",
        "aero-linux-aarch64.tar.gz",
    ):
        assert archive in script
    assert 'curl -fL --retry 3' in script
    assert '"$AERO_PACKAGE_URL.sha256"' in script
    assert "sha256sum -c" in script
    assert "shasum -a 256 -c" in script


def test_release_builder_produces_matching_archives_and_checksums():
    installer = Path("install.sh").read_text()
    builder = Path("scripts/release/build-download-packages.sh").read_text()

    assert "uv build --wheel" in builder
    assert 'cp "$ROOT/install.sh" "$DIST_DIR/install.sh"' in builder
    for archive in (
        "aero-macos-arm64.tar.gz",
        "aero-macos-x86_64.tar.gz",
        "aero-linux-x86_64.tar.gz",
        "aero-linux-aarch64.tar.gz",
    ):
        assert archive in installer
        assert archive in builder
    assert '"$ARCHIVE.sha256"' in builder
