# 安装与运行时

## 推荐安装

```bash
curl -LsSf https://aero.skyviewor.com/download/install.sh | sh
```

安装过程分为两层：

1. `uv tool` 将 `aero` CLI 安装到独立的 Python 3.12 环境。
2. `aero setup` 将 Micromamba 和科学计算环境安装到 `~/.aero/runtime/`。

Aero 不使用系统 Python，不向 Conda base 安装包，也不会复用或修改用户已有的
Miniconda、Anaconda、Miniforge 环境。

## 项目初始化

进入研究项目目录后执行：

```bash
aero init
aero chat
```

`aero init` 只在当前目录创建项目配置和工作目录，不安装软件，也不会继承父目录的
Aero 项目配置。

## 运行时模式

```bash
aero setup          # Python 3.12 基础环境，其他工具按需安装
aero setup --full   # 预装 CDO、NCO、ecCodes、GDAL、绘图等完整工具集
aero doctor         # 检查 Micromamba、环境 Python 和版本
aero runtime clean  # 删除 ~/.aero/runtime，项目数据不受影响
```

可通过 `AERO_RUNTIME_ROOT` 自定义运行时根目录。清理后再次执行 `aero setup` 即可重建。

## 自动化安装

```bash
AERO_SKIP_SETUP=1 ./install.sh  # 只安装 CLI
AERO_DOWNLOAD_BASE=https://mirror.example.com/download ./install.sh
```

中国大陆网络会沿用项目的 PyPI 与 Conda 镜像检测，也可用
`AERO_NETWORK_REGION=mainland_china` 显式指定。

## 构建网站分发包

发布前执行：

```bash
scripts/release/build-download-packages.sh
```

脚本先构建标准 Python wheel，再生成以下固定名称的归档及对应 `.sha256` 文件：

```text
aero-macos-arm64.tar.gz
aero-macos-x86_64.tar.gz
aero-linux-x86_64.tar.gz
aero-linux-aarch64.tar.gz
```

将 `dist/download/` 中的全部文件上传至 `https://aero.skyviewor.com/download/`。
构建脚本会把 `install.sh` 一并复制到该目录。平台归档当前包含同一个纯 Python wheel，
依赖 wheel 仍由 uv 根据用户实际平台选择；固定平台文件名为后续加入原生组件保留空间。
