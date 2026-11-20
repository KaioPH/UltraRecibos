"""
Executa todos os testes em uma pasta de dados temporária.

    python tests/executar_testes.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ambiente  # noqa: E402,F401  (prepara a pasta temporária)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(
        str(Path(__file__).resolve().parent), pattern="test_*.py",
        top_level_dir=str(ambiente.RAIZ)
    )
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"\nPasta temporária usada: {ambiente.PASTA}")
    sys.exit(0 if resultado.wasSuccessful() else 1)
