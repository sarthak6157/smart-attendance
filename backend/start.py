#!/usr/bin/env python3
"""
start.py — One-click launcher for the Smart Attendance System backend.

Usage:
    python start.py

What it does:
  1. Checks Python version (≥ 3.9 required)
  2. Creates a virtual environment  (venv/)  if it doesn't exist
  3. Installs all dependencies from requirements.txt
  4. Launches Flask on http://localhost:5000
"""

import sys, os, subprocess, platform

VENV_DIR   = os.path.join(os.path.dirname(__file__), 'venv')
REQ_FILE   = os.path.join(os.path.dirname(__file__), 'requirements.txt')
APP_MODULE = os.path.join(os.path.dirname(__file__), 'app.py')

CYAN  = '\033[96m'
GREEN = '\033[92m'
RED   = '\033[91m'
RESET = '\033[0m'
BOLD  = '\033[1m'


def banner(msg):
    print(f'\n{CYAN}{BOLD}» {msg}{RESET}')


def success(msg):
    print(f'{GREEN}✓ {msg}{RESET}')


def error(msg):
    print(f'{RED}✗ {msg}{RESET}')
    sys.exit(1)


# ── 1. Python version check ───────────────────────────────────────
banner('Checking Python version …')
major, minor = sys.version_info[:2]
if (major, minor) < (3, 9):
    error(f'Python 3.9+ required. You have {major}.{minor}.')
success(f'Python {major}.{minor} — OK')

# ── 2. Create virtual environment ────────────────────────────────
if not os.path.isdir(VENV_DIR):
    banner('Creating virtual environment …')
    subprocess.check_call([sys.executable, '-m', 'venv', VENV_DIR])
    success('venv created.')
else:
    success('venv already exists — skipping creation.')

# ── 3. Determine pip / python paths inside venv ──────────────────
is_win = platform.system() == 'Windows'
if is_win:
    venv_python = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    venv_pip    = os.path.join(VENV_DIR, 'Scripts', 'pip.exe')
else:
    venv_python = os.path.join(VENV_DIR, 'bin', 'python')
    venv_pip    = os.path.join(VENV_DIR, 'bin', 'pip')

# ── 4. Install dependencies ──────────────────────────────────────
banner('Installing dependencies (this may take a minute on first run) …')
subprocess.check_call([venv_pip, 'install', '--upgrade', 'pip', '-q'])
subprocess.check_call([venv_pip, 'install', '-r', REQ_FILE, '-q'])
success('All dependencies installed.')

# ── 5. Launch Flask ──────────────────────────────────────────────
banner('Starting Smart Attendance System backend …')
print(f'\n  {BOLD}URL  →  http://localhost:5000{RESET}')
print(f'  Press Ctrl+C to stop.\n')

os.environ['FLASK_APP'] = APP_MODULE
os.environ.setdefault('FLASK_DEBUG', '1')

os.execv(venv_python, [venv_python, APP_MODULE])
