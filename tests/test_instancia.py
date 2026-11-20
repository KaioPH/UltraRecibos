"""
Opção J: duas cópias do programa não podem ficar abertas juntas.
Usa processos separados (funciona no Windows e no Linux).
"""

import os
import subprocess
import sys
import time
import unittest

from tests import ambiente

CODIGO_FILHO = r"""
import sys, time
sys.path.insert(0, sys.argv[1])
import instancia_unica
print("ok" if instancia_unica.adquirir() else "ocupado", flush=True)
time.sleep(float(sys.argv[2]))
"""


def _abrir(espera):
    return subprocess.Popen(
        [sys.executable, "-c", CODIGO_FILHO, str(ambiente.RAIZ), str(espera)],
        stdout=subprocess.PIPE, text=True, env=dict(os.environ)
    )


class TestInstanciaUnica(unittest.TestCase):

    def test_segunda_copia_e_bloqueada_e_liberada_ao_fechar(self):
        primeira = _abrir(4)
        self.assertEqual(primeira.stdout.readline().strip(), "ok")

        segunda = _abrir(0)
        self.assertEqual(segunda.stdout.readline().strip(), "ocupado")
        segunda.wait(10)

        # Encerramento forçado (simula travamento): a trava é liberada
        primeira.kill()
        primeira.wait(10)
        time.sleep(0.3)

        terceira = _abrir(0)
        self.assertEqual(terceira.stdout.readline().strip(), "ok")
        terceira.wait(10)
        for p in (primeira, segunda, terceira):
            p.stdout.close()


if __name__ == "__main__":
    unittest.main()
