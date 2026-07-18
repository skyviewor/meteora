#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd "$(dirname "$0")/../.." && pwd)"
DIST_DIR="${AERO_DIST_DIR:-$ROOT/dist/download}"
WHEEL_DIR="$ROOT/dist/wheel"

command -v uv >/dev/null 2>&1 || {
    printf 'uv is required to build Aero distributions.\n' >&2
    exit 1
}

mkdir -p "$DIST_DIR" "$WHEEL_DIR"
find "$WHEEL_DIR" -type f -name '*.whl' -delete
uv build --wheel --out-dir "$WHEEL_DIR" "$ROOT"

WHEEL_COUNT="$(find "$WHEEL_DIR" -type f -name '*.whl' | wc -l | tr -d ' ')"
[ "$WHEEL_COUNT" = "1" ] || {
    printf 'Expected exactly one wheel, found %s.\n' "$WHEEL_COUNT" >&2
    exit 1
}
WHEEL_PATH="$(find "$WHEEL_DIR" -type f -name '*.whl' | head -n 1)"
cp "$ROOT/install.sh" "$DIST_DIR/install.sh"
chmod +x "$DIST_DIR/install.sh"

for ARCHIVE in \
    aero-macos-arm64.tar.gz \
    aero-macos-x86_64.tar.gz \
    aero-linux-x86_64.tar.gz \
    aero-linux-aarch64.tar.gz
do
    STAGING="$(mktemp -d "${TMPDIR:-/tmp}/aero-dist.XXXXXX")"
    cp "$WHEEL_PATH" "$STAGING/"
    tar -czf "$DIST_DIR/$ARCHIVE" -C "$STAGING" "$(basename "$WHEEL_PATH")"
    rm -rf "$STAGING"

    if command -v sha256sum >/dev/null 2>&1; then
        (cd "$DIST_DIR" && sha256sum "$ARCHIVE" > "$ARCHIVE.sha256")
    else
        HASH="$(shasum -a 256 "$DIST_DIR/$ARCHIVE" | awk '{print $1}')"
        printf '%s  %s\n' "$HASH" "$ARCHIVE" > "$DIST_DIR/$ARCHIVE.sha256"
    fi
    printf 'Built %s\n' "$DIST_DIR/$ARCHIVE"
done

printf 'Upload everything in %s to https://aero.skyviewor.com/download/\n' "$DIST_DIR"
