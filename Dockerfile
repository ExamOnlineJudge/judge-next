FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PORT=5055
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

WORKDIR /app

# Enable universe and install all toolchains & runtimes
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    software-properties-common \
    ca-certificates \
    curl \
    wget \
    gnupg \
    build-essential \
    pkg-config \
    gcc \
    g++ \
    clang \
    llvm \
    lld \
    nasm \
    yasm \
    fp-compiler \
    fpc \
    rustc \
    cargo \
    golang-go \
    openjdk-21-jdk-headless \
    python3 \
    python3-pip \
    python3-dev \
    nodejs \
    npm \
    php-cli \
    lua5.4 \
    luajit \
    mono-complete \
    mono-mcs \
    pypy3 \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g tsx 2>/dev/null || true

COPY . /app

EXPOSE 5055

CMD ["python3", "server.py"]
