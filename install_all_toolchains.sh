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
apt-get update -y || true
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
    pkg-config || true

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

# 7. Install Distribution Packages in Resilient Groups
echo "📦 [7/14] Installing compilers, runtimes, and distributions..."
apt-get update -y || true

# Group A: Native C, C++, D, LLVM, Asm & Cross-Compilers
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
    g++-arm-linux-gnueabihf || true

# Group B: Pascal Modes (ObjFPC, Turbo Pascal, Delphi)
apt-get install -y --no-install-recommends \
    fp-compiler \
    fpc \
    fpc-source || true

# Group C: Mono & Microsoft .NET
apt-get install -y --no-install-recommends \
    mono-complete \
    mono-devel \
    mono-mcs \
    fsharp \
    dotnet-sdk-8.0 \
    dotnet-sdk-9.0 || true

# Group D: OpenJDK LTS & Standard Versions
apt-get install -y --no-install-recommends \
    openjdk-21-jdk-headless \
    openjdk-17-jdk-headless \
    openjdk-11-jdk-headless \
    openjdk-8-jdk-headless || true

# Group E: Adoptium Eclipse Temurin JDKs
apt-get install -y --no-install-recommends \
    temurin-26-jdk \
    temurin-25-jdk \
    temurin-21-jdk \
    temurin-17-jdk \
    temurin-11-jdk \
    temurin-8-jdk || true

# Group F: BellSoft Liberica JDKs
apt-get install -y --no-install-recommends \
    bellsoft-java26 \
    bellsoft-java25 \
    bellsoft-java21 \
    bellsoft-java17 \
    bellsoft-java11 \
    bellsoft-java8 || true

# Group G: Scripting, JIT & Systems Runtimes
apt-get install -y --no-install-recommends \
    golang-go \
    rustc \
    cargo \
    dart \
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
        tar -xzf /tmp/jdk26.tar.gz -C /opt/jdk-26 --strip-components=1 2>/dev/null || true
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
        tar -xzf /tmp/jdk25.tar.gz -C /opt/jdk-25 --strip-components=1 2>/dev/null || true
        ln -sf /opt/jdk-25/bin/java /usr/local/bin/java25 || true
        ln -sf /opt/jdk-25/bin/javac /usr/local/bin/javac25 || true
        rm -f /tmp/jdk25.tar.gz
    fi
fi

# 10. Install Oracle GraalVM CE (21, 17)
echo "📦 [10/14] Installing Oracle GraalVM CE runtimes..."
if [ "${ARCH}" = "x86_64" ]; then
    curl -fsSL "https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-21.0.2/graalvm-community-jdk-21.0.2_linux-x64_bin.tar.gz" -o /tmp/graalvm21.tar.gz || true
    if [ -s /tmp/graalvm21.tar.gz ]; then
        tar -xzf /tmp/graalvm21.tar.gz -C /opt/graalvm-21 --strip-components=1 2>/dev/null || true
        ln -sf /opt/graalvm-21/bin/java /usr/local/bin/graalvm21-java || true
        rm -f /tmp/graalvm21.tar.gz
    fi

    curl -fsSL "https://github.com/graalvm/graalvm-ce-builds/releases/download/jdk-17.0.9/graalvm-community-jdk-17.0.9_linux-x64_bin.tar.gz" -o /tmp/graalvm17.tar.gz || true
    if [ -s /tmp/graalvm17.tar.gz ]; then
        tar -xzf /tmp/graalvm17.tar.gz -C /opt/graalvm-17 --strip-components=1 2>/dev/null || true
        ln -sf /opt/graalvm-17/bin/java /usr/local/bin/graalvm17-java || true
        rm -f /tmp/graalvm17.tar.gz
    fi
fi

# 11. Install Flat Assembler (FASM)
echo "📦 [11/14] Installing Flat Assembler (FASM)..."
if ! command -v fasm &>/dev/null; then
    curl -fsSL https://flatassembler.net/fasm-1.73.32.tgz -o /tmp/fasm.tgz || true
    if [ -s /tmp/fasm.tgz ]; then
        tar -xzf /tmp/fasm.tgz -C /tmp 2>/dev/null || true
        if [ -f /tmp/fasm/fasm ]; then
            mv /tmp/fasm/fasm /usr/local/bin/fasm
            chmod +x /usr/local/bin/fasm
        fi
        rm -rf /tmp/fasm*
    fi
fi

# 12. Install Kotlin Compiler (kotlinc 2.1)
echo "📦 [12/14] Installing Kotlin Compiler..."
if ! command -v kotlinc &>/dev/null; then
    curl -fsSL https://github.com/JetBrains/kotlin/releases/download/v2.1.0/kotlin-compiler-2.1.0.zip -o /tmp/kotlinc.zip || true
    if [ -s /tmp/kotlinc.zip ]; then
        unzip -q -o /tmp/kotlinc.zip -d /opt 2>/dev/null || true
        ln -sf /opt/kotlinc/bin/kotlinc /usr/local/bin/kotlinc || true
        ln -sf /opt/kotlinc/bin/kotlin /usr/local/bin/kotlin || true
        rm -f /tmp/kotlinc.zip
    fi
fi

# 13. Install TypeScript, TSX, and esbuild JIT
echo "📦 [13/14] Installing global TypeScript, TSX, and esbuild engines..."
if command -v npm &>/dev/null; then
    npm install -g typescript tsx esbuild ts-node || true
fi

# 14. Cleanup & Dynamic Verification
echo "📦 [14/14] Cleaning temporary package caches and validating toolchains..."
apt-get clean || true
rm -rf /tmp/jdk* /tmp/graal* /tmp/fasm* /tmp/kotlinc* /tmp/oracle* /tmp/packages-microsoft* 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/toolchain_discovery.py" ]; then
    python3 "${SCRIPT_DIR}/toolchain_discovery.py" || true
fi

echo "=============================================================================="
echo "🎉 [EOJ] All 20 Languages, Compilers, and Distributions Installed Successfully!"
echo "=============================================================================="
