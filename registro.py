
"""
Registro de funcionamento (log) do Ultra Recibos.

No executável não existe console, então mensagens de
erro e avisos são gravadas em dados/logs/ultrarecibos.log
(rotação automática: 5 arquivos de até 1 MB).

O log nunca registra CPF, nome de aluno ou valores.
"""

import logging
import sys

from logging.handlers import RotatingFileHandler

from caminhos import PASTA_LOGS


_configurado = False


def obter_logger(nome="ultrarecibos"):

    global _configurado

    logger = logging.getLogger("ultrarecibos")

    if not _configurado:

        _configurado = True
        logger.setLevel(logging.INFO)

        formato = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        try:
            PASTA_LOGS.mkdir(parents=True, exist_ok=True)

            arquivo = RotatingFileHandler(
                PASTA_LOGS / "ultrarecibos.log",
                maxBytes=1_000_000,
                backupCount=5,
                encoding="utf-8"
            )
            arquivo.setFormatter(formato)
            logger.addHandler(arquivo)

        except OSError:
            # Sem permissão de escrita: segue sem log em arquivo
            pass

        # Console somente quando existir (Python / VS Code)
        if sys.stderr is not None:
            console = logging.StreamHandler(sys.stderr)
            console.setFormatter(formato)
            logger.addHandler(console)

    if nome == "ultrarecibos":
        return logger

    return logger.getChild(nome)
