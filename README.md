# ⚡ EOJ Judge Server

Sandboxed Multi-Language Execution & PTY Interactive Daemon for the EOJ Platform.

---

## 🚀 Quick Start (Docker)

```bash
# From project root
docker compose up -d --build
```

- **Health Check**: `http://localhost:5055/api/health`
- **Dynamic Languages & Toolchains API**: `http://localhost:5055/api/languages`

---

## 🛠️ Direct Host Setup (Ubuntu/Debian)

```bash
sudo chmod +x install_all_toolchains.sh
sudo ./install_all_toolchains.sh
python3 server.py
```

For full documentation, see [`/home/pc/Documents/EOJ/INSTALLATION_GUIDE.md`](file:///home/pc/Documents/EOJ/INSTALLATION_GUIDE.md).
