#!/usr/bin/env python3
"""Entry point for direct invocation: python3 run.py <command>

This script sets up the package path so relative imports work,
then delegates to md_linker.cli.main().
"""
import sys
from pathlib import Path

# Ensure the package root is on sys.path
_root = str(Path(__file__).resolve().parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from md_linker.cli import main

main()
