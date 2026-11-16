#!/usr/bin/env python3
"""
run_desktop.py
==============
Ponto de entrada do PeptMass desktop (o executavel da Release).

Abre a mesma interface da versao web numa janela propria, com um servidor
interno so para este computador. Execute:
    python run_desktop.py
"""

from peptmass.desktop.app import main

if __name__ == "__main__":
    main()
