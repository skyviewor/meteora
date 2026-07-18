#!/usr/bin/env sh
set -eu

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info() { printf "  ${CYAN}[*]${NC} %s\n" "$*"; }
ok() { printf "  ${GREEN}[OK]${NC} %s\n" "$*"; }
fail() { printf "  ${RED}[X]${NC} %s\n" "$*" >&2; exit 1; }

OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS:$ARCH" in
    Darwin:arm64|Darwin:aarch64) ARCHIVE_FILE="aero-macos-arm64.tar.gz" ;;
    Darwin:x86_64) ARCHIVE_FILE="aero-macos-x86_64.tar.gz" ;;
    Linux:x86_64|Linux:amd64) ARCHIVE_FILE="aero-linux-x86_64.tar.gz" ;;
    Linux:arm64|Linux:aarch64) ARCHIVE_FILE="aero-linux-aarch64.tar.gz" ;;
    *) fail "不支持的平台: $OS / $ARCH" ;;
esac

AERO_DOWNLOAD_BASE="${AERO_DOWNLOAD_BASE:-https://aero.skyviewor.com/download}"
AERO_PACKAGE_URL="$AERO_DOWNLOAD_BASE/$ARCHIVE_FILE"
NETWORK_REGION="${AERO_NETWORK_REGION:-}"
if [ -z "$NETWORK_REGION" ]; then
    TIMEZONE="${TZ:-$(readlink /etc/localtime 2>/dev/null || true)}"
    case "$TIMEZONE" in
        *Asia/Shanghai|*Asia/Chongqing|*Asia/Harbin) NETWORK_REGION="mainland_china" ;;
        *) NETWORK_REGION="global" ;;
    esac
fi
case "$NETWORK_REGION" in
    cn|china|mainland|mainland_china)
        export UV_DEFAULT_INDEX="${UV_DEFAULT_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
        export PIP_INDEX_URL="${PIP_INDEX_URL:-$UV_DEFAULT_INDEX}"
        ;;
esac

printf "${BOLD}${CYAN}Aero - 气象科研 AI Agent IDE${NC}\n\n"

if ! command -v curl >/dev/null 2>&1; then
    fail "安装需要 curl，请先安装后重试"
fi

if ! command -v uv >/dev/null 2>&1; then
    info "安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    export PATH
fi
command -v uv >/dev/null 2>&1 || fail "uv 安装完成，但当前 shell 尚未找到 uv"
ok "uv 已就绪: $(command -v uv)"

TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/aero-install.XXXXXX")"
trap 'rm -rf "$TEMP_DIR"' EXIT HUP INT TERM
ARCHIVE_PATH="$TEMP_DIR/$ARCHIVE_FILE"
CHECKSUM_PATH="$ARCHIVE_PATH.sha256"

info "下载 Aero 分发包: $AERO_PACKAGE_URL"
curl -fL --retry 3 --connect-timeout 10 "$AERO_PACKAGE_URL" -o "$ARCHIVE_PATH"
curl -fL --retry 3 --connect-timeout 10 "$AERO_PACKAGE_URL.sha256" -o "$CHECKSUM_PATH"

info "校验分发包完整性..."
if command -v sha256sum >/dev/null 2>&1; then
    (cd "$TEMP_DIR" && sha256sum -c "$ARCHIVE_FILE.sha256")
elif command -v shasum >/dev/null 2>&1; then
    (cd "$TEMP_DIR" && shasum -a 256 -c "$ARCHIVE_FILE.sha256")
else
    fail "系统缺少 sha256sum 或 shasum，无法校验安装包"
fi

PACKAGE_DIR="$TEMP_DIR/package"
mkdir -p "$PACKAGE_DIR"
tar -xzf "$ARCHIVE_PATH" -C "$PACKAGE_DIR"
WHEEL_COUNT="$(find "$PACKAGE_DIR" -type f -name '*.whl' | wc -l | tr -d ' ')"
[ "$WHEEL_COUNT" = "1" ] || fail "分发包格式错误：应包含且仅包含一个 wheel"
WHEEL_PATH="$(find "$PACKAGE_DIR" -type f -name '*.whl' | head -n 1)"

info "安装 Aero CLI（独立 Python 3.12 环境）..."
uv tool install --python 3.12 --force "$WHEEL_PATH"

UV_BIN_DIR="$(uv tool dir --bin 2>/dev/null || true)"
if [ -n "$UV_BIN_DIR" ]; then
    PATH="$UV_BIN_DIR:$PATH"
    export PATH
fi
command -v aero >/dev/null 2>&1 || {
    uv tool update-shell >/dev/null 2>&1 || true
    fail "Aero 已安装，但当前 shell 尚未找到 aero；请重开终端后运行 aero setup"
}
ok "Aero CLI 已安装: $(command -v aero)"

if [ "${AERO_SKIP_SETUP:-0}" = "1" ]; then
    info "已按 AERO_SKIP_SETUP=1 跳过运行时安装"
else
    info "安装 Aero 私有基础运行时..."
    aero setup --yes
    ok "私有运行时已就绪"
fi

printf "\n${BOLD}${GREEN}安装完成${NC}\n"
printf "  进入研究目录后运行：\n"
printf "    ${BOLD}aero init${NC}\n"
printf "    ${BOLD}aero chat${NC}\n\n"
printf "  环境检查：${BOLD}aero doctor${NC}\n"
printf "  完整工具集：${BOLD}aero setup --full${NC}\n"
