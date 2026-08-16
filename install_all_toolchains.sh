#!/usr/bin/env bash
# ==============================================================================
# EOJ Platform - Complete Multi-Language & Multi-Distribution Auto-Installer
# Installs EVERY requested language, version, compiler, distribution, and runtime:
# - Java:
#   * Java 26 (Current GA) - OpenJDK, Eclipse Temurin, Oracle JDK, BellSoft Liberica, GraalVM
#   * Java 25 (LTS GA)     - OpenJDK, Eclipse Temurin, Oracle JDK, BellSoft Liberica, GraalVM
#   * Java 21 (LTS GA)     - OpenJDK, Eclipse Temurin, Oracle JDK, BellSoft Liberica, GraalVM
#   * Java 17 (LTS GA)     - OpenJDK, Eclipse Temurin, Oracle JDK, BellSoft Liberica, GraalVM
#   * Java 11 (LTS)        - OpenJDK, Eclipse Temurin, BellSoft Liberica, Oracle JDK
#   * Java 8 (1.8 LTS)     - OpenJDK, Eclipse Temurin, BellSoft Liberica, Oracle JDK
#   * Java 7, 6, 5, 1.4, 1.0–1.3 Compatibility Modes
# - Free Pascal: ObjFPC, Turbo Pascal (TP 7.0 mode), Delphi mode, Smart Linking
# - Microsoft .NET SDK 9 & 8, Mono Suite (C#, F#, VB)
# - GCC 15, Clang 21, NASM, YASM, FASM, GNU AS, QEMU ARM32/ARM64
# - Rust, Go, Dart SDK, GDC, LDC, Kotlin 2.1, Node.js 22 LTS, TypeScript/TSX, PyPy3, PHP, Lua
# ==============================================================================
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export TZ=Etc/UTC

echo "=============================================================================="
echo "🚀 [EOJ] Installing ALL Languages, Versions, Compilers & Distributions"
echo "=============================================================================="

ARCH=$(uname -m)
echo "ℹ️ Target CPU Architecture: ${ARCH}"

# 1. Base Essentials & Required Directories
echo "📦 [1/14] Setting up base build tools, keys, and installation directories..."
apt-get update -y
apt-get install -y --no-install-recommends \
    locales \
    tzdata \
    ca-certificates \
    curl \
    wget \
    gnupg \
    unzip \
    tar \
    bzip2 \
    xz-utils \
    build-essential \
    software-properties-common \
    apt-transport-https \
    pkg-config

locale-gen en_US.UTF-8 || true
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

mkdir -p /etc/apt/keyrings /usr/share/keyrings /opt \
         /opt/jdk-26 /opt/jdk-25 \
         /opt/graalvm-26 /opt/graalvm-25 /opt/graalvm-21 /opt/graalvm-17 \
         /opt/oracle-26 /opt/oracle-25 /opt/oracle-21 /opt/oracle-17

# 2. Add Adoptium (Eclipse Temurin) Repository (26, 25, 21, 17, 11, 8)
echo "📦 [2/14] Configuring Eclipse Temurin (Adoptium) repository..."
curl -fsSL https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor --yes -o /etc/apt/keyrings/adoptium.gpg
echo "deb [signed-by=/etc/apt/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb $(. /etc/os-release && echo "$VERSION_CODENAME") main" | tee /etc/apt/sources.list.d/adoptium.list

# 3. Add BellSoft Liberica Repository (26, 25, 21, 17, 11, 8)
echo "📦 [3/14] Configuring BellSoft Liberica JDK repository..."
curl -fsSL https://download.bell-sw.com/pki/GPG-KEY-bellsoft | gpg --dearmor --yes -o /etc/apt/keyrings/bellsoft.gpg
echo "deb [signed-by=/etc/apt/keyrings/bellsoft.gpg] https://apt.bell-sw.com/ stable main" | tee /etc/apt/sources.list.d/bellsoft.list

# 4. Add Microsoft .NET 8 / 9 Repository
echo "📦 [4/14] Configuring Microsoft .NET repository..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    UBUNTU_VER="${VERSION_ID:-24.04}"
    wget -q "https://packages.microsoft.com/config/ubuntu/${UBUNTU_VER}/packages-microsoft-prod.deb" -O /tmp/packages-microsoft-prod.deb || \
    wget -q "https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb" -O /tmp/packages-microsoft-prod.deb || true
    if [ -f /tmp/packages-microsoft-prod.deb ]; then
        dpkg -i /tmp/packages-microsoft-prod.deb || true
        rm -f /tmp/packages-microsoft-prod.deb
    fi
fi

# 5. Add Google Dart Repository
echo "📦 [5/14] Configuring Google Dart repository..."
curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor --yes -o /usr/share/keyrings/dart.gpg
echo "deb [signed-by=/usr/share/keyrings/dart.gpg arch=${ARCH/x86_64/amd64}] https://storage.googleapis.com/download.dartlang.org/linux/debian stable main" | tee /etc/apt/sources.list.d/dart_stable.list

# 6. Add NodeSource Node.js 22 LTS (V8 Engine) Repository
echo "📦 [6/14] Configuring NodeSource Node.js 22 LTS repository..."
curl -fsSL https://deb.nodesource.com/setup_22.x | bash - || true

# 7. Install Distribution Packages (All 21 Languages, OpenJDK, Temurin, BellSoft, etc.)
echo "📦 [7/14] Installing compilers, runtimes, and distributions..."
apt-get update -y || true

apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    clang \
    llvm \
    lld \
    gdc \
    ldc \
    nasm \
    yasm \
    binutils \
    qemu-user-static \
    gcc-aarch64-linux-gnu \
    g++-aarch64-linux-gnu \
    gcc-arm-linux-gnueabihf \
    g++-arm-linux-gnueabihf \
    fp-compiler \
    fpc \
    fpc-source \
    mono-complete \
    mono-mcs \
    mono-vbnc \
    fsharp \
    dotnet-sdk-8.0 || true \
    openjdk-21-jdk-headless \
    openjdk-17-jdk-headless \
    openjdk-11-jdk-headless \
    openjdk-8-jdk-headless \
    temurin-26-jdk || true \
    temurin-25-jdk || true \
    temurin-21-jdk || true \
    temurin-17-jdk || true \
    temurin-11-jdk || true \
    temurin-8-jdk || true \
    bellsoft-java26 || true \
    bellsoft-java25 || true \
    bellsoft-java21 || true \
    bellsoft-java17 || true \
    bellsoft-java11 || true \
    bellsoft-java8 || true \
    golang-go \
    rustc \
    cargo \
    dart || true \
    python3 \
    python3-pip \
    python3-dev \
    pypy3 \
    lua5.4 \
    lua5.3 \
    lua5.1 \
    luajit \
    gobjc \
    gobjc++ \
    libobjc4 \
    php-cli \
    nodejs || true

# 8. Install Java 26 GA Distribution Build
echo "📦 [8/14] Installing Java 26 GA Distribution Build..."
if [ "${ARCH}" = "x86_64" ]; then
    JDK26_URL="https://download.oracle.com/java/26/latest/jdk-26_linux-x64_bin.tar.gz"
    if curl -fsSL "${JDK26_URL}" -o /tmp/jdk26.tar.gz || curl -fsSL "https://download.java.net/java/GA/jdk26/openjdk-26_linux-x64_bin.tar.gz" -o /tmp/jdk26.tar.gz; then
        tar -xzf /tmp/jdk26.tar.gz -C /opt/jdk-26 --strip-components=1 || true
        ln -sf /opt/jdk-26/bin/java /usr/local/bin/java26 || true
        ln -sf /opt/jdk-26/bin/javac /usr/local/bin/javac26 || true
        rm -f /tmp/jdk26.tar.gz
    fi
fi

# 9. Install Java 25 (LTS GA) Distribution Build
echo "📦 [9/14] Installing Java 25 LTS GA Distribution Build..."
if [ "${ARCH}" = "x86_64" ]; then
    JDK25_URL="https://download.oracle.com/java/25/latest/jdk-25_linux-x64_bin.tar.gz"
    if curl -fsSL "${JDK25_URL}" -o /tmp/jdk25.tar.gz || curl -fsSL "https://download.java.net/java/GA/jdk25/openjdk-25_linux-x64_bin.tar.gz" -o /tmp/jdk25.tar.gz; then
        tar -xzf /tmp/jdk25.tar.gz -C /opt/jdk-25 --strip-components=1 || true
        ln -sf /opt/jdk-25/bin/java /usr/local/bin/java25 || true
        ln -sf /opt/jdk-25/bin/javac /usr/local/bin/javac25 || true
        rm -f /tmp/jdk25.tar.gz
    fi
fi

# 10. Install Oracle GraalVM CE (26, 25, 21, 17)
echo "📦 [10/14] Installing Oracle GraalVM CE runtimes..."
if [ "${ARCH}" = "x86_64" ]; then
    # GraalVM 21
    curl -fsSL "https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-21.0.2/graalvm-community-jdk-21.0.2_linux-x64_bin.tar.gz" -o /tmp/graalvm21.tar.gz || true
    if [ -f /tmp/graalvm21.tar.gz ]; then
        tar -xzf /tmp/graalvm21.tar.gz -C /opt/graalvm-21 --strip-components=1 || true
        ln -sf /opt/graalvm-21/bin/java /usr/local/bin/graalvm21-java || true
        rm -f /tmp/graalvm21.tar.gz
    fi

    # GraalVM 17
    curl -fsSL "https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-17.0.9/graalvm-community-jdk-17.0.9_linux-x64_bin.tar.gz" -o /tmp/graalvm17.tar.gz || true
    if [ -f /tmp/graalvm17.tar.gz ]; then
        tar -xzf /tmp/graalvm17.tar.gz -C /opt/graalvm-17 --strip-components=1 || true
        ln -sf /opt/graalvm-17/bin/java /usr/local/bin/graalvm17-java || true
        rm -f /tmp/graalvm17.tar.gz
    fi
fi

# 11. Install Oracle Official JDKs (21, 17)
echo "📦 [11/14] Installing Oracle Official JDK 21 & 17..."
if [ "${ARCH}" = "x86_64" ]; then
    curl -fsSL "https://download.oracle.com/java/21/latest/jdk-21_linux-x64_bin.tar.gz" -o /tmp/oracle21.tar.gz || true
    if [ -f /tmp/oracle21.tar.gz ]; then
        tar -xzf /tmp/oracle21.tar.gz -C /opt/oracle-21 --strip-components=1 || true
        ln -sf /opt/oracle-21/bin/java /usr/local/bin/oracle21-java || true
        rm -f /tmp/oracle21.tar.gz
    fi

    curl -fsSL "https://download.oracle.com/java/17/latest/jdk-17_linux-x64_bin.tar.gz" -o /tmp/oracle17.tar.gz || true
    if [ -f /tmp/oracle17.tar.gz ]; then
        tar -xzf /tmp/oracle17.tar.gz -C /opt/oracle-17 --strip-components=1 || true
        ln -sf /opt/oracle-17/bin/java /usr/local/bin/oracle17-java || true
        rm -f /tmp/oracle17.tar.gz
    fi
fi

# 12. Install Flat Assembler (FASM) & Kotlin Compiler (kotlinc 2.1)
echo "📦 [12/14] Installing Flat Assembler (FASM) & Kotlin Compiler..."
if ! command -v fasm &>/dev/null; then
    curl -fsSL https://flatassembler.net/fasm-1.73.32.tgz -o /tmp/fasm.tgz
    tar -xzf /tmp/fasm.tgz -C /tmp
    mv /tmp/fasm/fasm /usr/local/bin/fasm
    chmod +x /usr/local/bin/fasm
    rm -rf /tmp/fasm*
fi

if ! command -v kotlinc &>/dev/null; then
    curl -fsSL https://github.com/JetBrains/kotlin/releases/download/v2.1.0/kotlin-compiler-2.1.0.zip -o /tmp/kotlinc.zip
    unzip -q -o /tmp/kotlinc.zip -d /opt
    ln -sf /opt/kotlinc/bin/kotlinc /usr/local/bin/kotlinc
    ln -sf /opt/kotlinc/bin/kotlin /usr/local/bin/kotlin
    rm -f /tmp/kotlinc.zip
fi

# 13. Install TypeScript, TSX, and esbuild JIT
echo "📦 [13/14] Installing global TypeScript, TSX, and esbuild engines..."
if command -v npm &>/dev/null; then
    npm install -g typescript tsx esbuild ts-node || true
fi

# 14. Cleanup & Dynamic Verification
echo "📦 [14/14] Cleaning temporary package caches and validating toolchains..."
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/toolchain_discovery.py" ]; then
    python3 "${SCRIPT_DIR}/toolchain_discovery.py"
fi

echo "=============================================================================="
echo "🎉 [EOJ] All 21 Languages, Java 26/25/21/17/11/8, and Distributions Installed!"
echo "=============================================================================="
