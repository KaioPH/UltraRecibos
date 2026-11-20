"""
Ambiente isolado para os testes automatizados.

Define ULTRARECIBOS_DADOS para uma pasta temporária ANTES de
importar qualquer módulo do programa. Nenhum teste usa a pasta
de dados real nem dados reais de alunos (somente fictícios).
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

if "ULTRARECIBOS_DADOS" not in os.environ:
    os.environ["ULTRARECIBOS_DADOS"] = tempfile.mkdtemp(prefix="ultrarecibos_teste_")

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import caminhos  # noqa: E402

PASTA = Path(os.environ["ULTRARECIBOS_DADOS"]).resolve()

# Trava de segurança: jamais rodar sobre a pasta real
assert caminhos.PASTA_DADOS.resolve() == PASTA, "Pasta de testes inválida"
assert "ultrarecibos_teste_" in str(PASTA) or os.environ.get("ULTRARECIBOS_TESTE_OK") == "1"


def reiniciar_dados():
    """
    Apaga somente o conteúdo da pasta temporária de testes.
    """

    for item in PASTA.iterdir():
        # No Windows, o arquivo de log fica aberto pelo programa enquanto
        # os testes rodam e não pode ser apagado: a pasta logs é mantida.
        if item.name in ("logs", ".instancia.lock"):
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    caminhos.PASTA_PDFS.mkdir(parents=True, exist_ok=True)


# Dados fictícios (CPFs válidos apenas matematicamente)
RECIBO_FICTICIO = dict(
    nome="Cliente Ficticio Um",
    cpf="52998224725",
    codigo_aluno="000123",
    plano="Gold Pro",
    valor_centavos=12990,
    forma_pagamento="Crédito",
    data_pagamento="2026-11-10",
    consultor="Consultor Teste",
    codigo_autenticacao="00A12",
)
