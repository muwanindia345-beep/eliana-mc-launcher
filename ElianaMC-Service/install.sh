#!/bin/bash

# ══════════════════════════════════════════════
#   ElianaMC Service — Secure Auto Installer
#   Supports: Ubuntu, Debian, Kali, NetHunter,
#             Termux
# ══════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

clear
echo -e "${CYAN}"
echo "  ███████╗██╗     ██╗ █████╗ ███╗   ██╗ █████╗ "
echo "  ██╔════╝██║     ██║██╔══██╗████╗  ██║██╔══██╗"
echo "  █████╗  ██║     ██║███████║██╔██╗ ██║███████║"
echo "  ██╔══╝  ██║     ██║██╔══██║██║╚██╗██║██╔══██║"
echo "  ███████╗███████╗██║██║  ██║██║ ╚████║██║  ██║"
echo "  ╚══════╝╚══════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝"
echo -e "${NC}"
echo -e "${BLUE}  ElianaMC Service — Secure Installer v1.0${NC}"
echo "  ════════════════════════════════════════"
echo ""

# ── Security: Password check ──────────────────
echo -e "${YELLOW}🔐 Security Verification${NC}"
read -sp "   Enter install password: " INPUT_PASS
echo ""

# Hash check (SHA256)
CORRECT_HASH="$(echo -n 'eliana2024' | sha256sum | awk '{print $1}')"
INPUT_HASH="$(echo -n "$INPUT_PASS" | sha256sum | awk '{print $1}')"

if [ "$INPUT_HASH" != "$CORRECT_HASH" ]; then
  echo -e "${RED}❌ Wrong password! Access denied.${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Password correct!${NC}"
echo ""

# ── Detect environment ────────────────────────
echo -e "${BLUE}🔍 Detecting environment...${NC}"

IS_TERMUX=false
IS_ROOT=false

if [ -d "/data/data/com.termux" ] || [ -n "$TERMUX_VERSION" ]; then
  IS_TERMUX=true
  ENV_NAME="Termux"
elif [ "$EUID" -eq 0 ]; then
  IS_ROOT=true
fi

# Detect distro
if [ "$IS_TERMUX" = true ]; then
  DISTRO="termux"
elif [ -f /etc/os-release ]; then
  source /etc/os-release
  DISTRO="${ID,,}"
else
  DISTRO="unknown"
fi

echo -e "${GREEN}✅ Environment: ${ENV_NAME:-$DISTRO}${NC}"
echo ""

# ── Install function ──────────────────────────
install_pkg() {
  if [ "$IS_TERMUX" = true ]; then
    pkg install -y "$1" 2>/dev/null || apt install -y "$1" 2>/dev/null
  else
    apt install -y "$1" 2>/dev/null || \
    yum install -y "$1" 2>/dev/null || \
    pacman -S --noconfirm "$1" 2>/dev/null
  fi
}

pip_install() {
  if [ "$IS_TERMUX" = true ]; then
    pip install "$1" 2>/dev/null
  else
    pip3 install "$1" --break-system-packages 2>/dev/null || \
    pip3 install "$1" 2>/dev/null
  fi
}

# ── Update system ─────────────────────────────
echo -e "${BLUE}📦 Updating packages...${NC}"
if [ "$IS_TERMUX" = true ]; then
  pkg update -y && pkg upgrade -y
else
  apt update -y 2>/dev/null || yum update -y 2>/dev/null
fi
echo -e "${GREEN}✅ Done${NC}"

# ── Python ────────────────────────────────────
echo -e "${BLUE}🐍 Installing Python...${NC}"
if [ "$IS_TERMUX" = true ]; then
  pkg install -y python
else
  install_pkg python3
  install_pkg python3-pip
fi
echo -e "${GREEN}✅ Python: $(python3 --version 2>/dev/null || python --version)${NC}"

# ── Java ──────────────────────────────────────
echo -e "${BLUE}☕ Installing Java...${NC}"
if [ "$IS_TERMUX" = true ]; then
  pkg install -y openjdk-21
else
  install_pkg openjdk-21-jre-headless 2>/dev/null || \
  install_pkg openjdk-17-jre-headless 2>/dev/null || \
  echo -e "${YELLOW}⚠️  Install Java manually${NC}"
fi
java -version 2>/dev/null && echo -e "${GREEN}✅ Java installed${NC}" || echo -e "${YELLOW}⚠️  Java not found${NC}"

# ── Python packages ───────────────────────────
echo -e "${BLUE}📦 Installing Python packages...${NC}"
for pkg in fastapi uvicorn httpx psutil; do
  pip_install "$pkg"
  python3 -c "import $pkg" 2>/dev/null && \
    echo -e "${GREEN}  ✅ $pkg${NC}" || \
    echo -e "${RED}  ❌ $pkg failed${NC}"
done

# ── stdbuf ────────────────────────────────────
echo -e "${BLUE}🔧 Installing coreutils...${NC}"
if [ "$IS_TERMUX" = true ]; then
  pkg install -y coreutils
else
  install_pkg coreutils
fi
echo -e "${GREEN}✅ Done${NC}"

# ── box64 ─────────────────────────────────────
echo -e "${BLUE}🪨 Checking box64 (Bedrock)...${NC}"
if command -v box64 &>/dev/null; then
  echo -e "${GREEN}✅ box64 already installed${NC}"
else
  echo -e "${YELLOW}⚠️  box64 not found${NC}"
  if [ "$IS_TERMUX" = true ]; then
    pkg install -y box64 2>/dev/null || \
    echo -e "${YELLOW}   Install box64 manually for Bedrock${NC}"
  else
    echo -e "${YELLOW}   Install box64 manually for Bedrock${NC}"
  fi
fi

# ── Setup directories ─────────────────────────
echo -e "${BLUE}📁 Setting up directories...${NC}"
if [ "$IS_TERMUX" = true ]; then
  BASE="$HOME"
else
  BASE="/root"
fi

mkdir -p "$BASE/SeraphinaMC"
mkdir -p "$BASE/LuciaMC"
echo -e "${GREEN}✅ Directories ready${NC}"

# ── Permissions ───────────────────────────────
echo -e "${BLUE}🔒 Setting permissions...${NC}"
chmod +x "$BASE/SeraphinaMC/ElianaMC-Service/start.sh" 2>/dev/null
chmod +x "$BASE/SeraphinaMC/ElianaMC-Service/install.sh" 2>/dev/null
echo -e "${GREEN}✅ Done${NC}"

# ── Update paths for Termux ───────────────────
if [ "$IS_TERMUX" = true ]; then
  echo -e "${BLUE}📝 Updating paths for Termux...${NC}"
  SFILE="$BASE/SeraphinaMC/ElianaMC-Service/backend.py"
  if [ -f "$SFILE" ]; then
    sed -i "s|/root/SeraphinaMC|$BASE/SeraphinaMC|g" "$SFILE"
    sed -i "s|/root/LuciaMC|$BASE/LuciaMC|g" "$SFILE"
    echo -e "${GREEN}✅ Paths updated${NC}"
  fi
fi

# ── Final summary ─────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════${NC}"
echo -e "${GREEN}  ✅ Installation Complete!${NC}"
echo ""
echo -e "${BLUE}  📋 Summary:${NC}"
python3 -c "import fastapi; print('     ✅ FastAPI')" 2>/dev/null  || echo "     ❌ FastAPI"
python3 -c "import uvicorn; print('     ✅ Uvicorn')" 2>/dev/null  || echo "     ❌ Uvicorn"
python3 -c "import httpx;   print('     ✅ httpx')"   2>/dev/null  || echo "     ❌ httpx"
python3 -c "import psutil;  print('     ✅ psutil')"  2>/dev/null  || echo "     ❌ psutil"
command -v java   &>/dev/null && echo "     ✅ Java"    || echo "     ❌ Java"
command -v box64  &>/dev/null && echo "     ✅ box64"   || echo "     ⚠️  box64 (optional)"
echo ""
echo -e "${YELLOW}  🚀 Start: ./start.sh${NC}"
echo -e "${CYAN}══════════════════════════════════════${NC}"
