
"""
Caminhos de dados e de recursos do Ultra Recibos.

- Executável (.exe): dados em %LOCALAPPDATA%\\UltraRecibos
- Python / VS Code: dados na subpasta "dados" do projeto
- Testes: a variável de ambiente ULTRARECIBOS_DADOS substitui
  a pasta de dados (nunca use dados reais em testes).
"""

from pathlib import Path
import os
import sys


# =========================================
# IDENTIFICA O AMBIENTE DE EXECUÇÃO
# =========================================

EXECUTAVEL = bool(getattr(sys, "frozen", False))

_pasta_teste = os.environ.get("ULTRARECIBOS_DADOS")

if _pasta_teste:

    # Pasta isolada para testes automatizados
    PASTA_DADOS = Path(_pasta_teste)

elif EXECUTAVEL:

    # Programa executado como .exe
    pasta_local = os.environ.get("LOCALAPPDATA")

    if pasta_local:
        PASTA_DADOS = Path(pasta_local) / "UltraRecibos"
    else:
        PASTA_DADOS = (
            Path.home()
            / "AppData"
            / "Local"
            / "UltraRecibos"
        )

else:

    # Programa executado pelo Python / VS Code
    PASTA_DADOS = (
        Path(__file__).resolve().parent
        / "dados"
    )


# =========================================
# CRIA A ESTRUTURA DE ARMAZENAMENTO
# =========================================

PASTA_DADOS.mkdir(
    parents=True,
    exist_ok=True
)

# Caminho do banco SQLite
CAMINHO_BANCO = PASTA_DADOS / "recibos.db"

# Pasta dos documentos PDF
PASTA_PDFS = PASTA_DADOS / "pdfs"

PASTA_PDFS.mkdir(
    parents=True,
    exist_ok=True
)

# Pasta das cópias de segurança
PASTA_BACKUPS = PASTA_DADOS / "backups"

# Pasta dos registros de funcionamento (logs)
PASTA_LOGS = PASTA_DADOS / "logs"


# =========================================
# RECURSOS VISUAIS (ASSETS)
# =========================================

def caminho_asset(nome):
    """
    Retorna o caminho de um arquivo da pasta assets,
    tanto no Python quanto no executável.
    """

    if EXECUTAVEL:
        pasta_base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        pasta_base = Path(__file__).resolve().parent

    return pasta_base / "assets" / nome
