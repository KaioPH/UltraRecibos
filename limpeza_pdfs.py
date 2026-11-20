
import re
import sqlite3

from contextlib import closing
from datetime import datetime, timedelta

from caminhos import PASTA_PDFS, CAMINHO_BANCO
from configuracoes import DIAS_RETENCAO
from registro import obter_logger


log = obter_logger("limpeza")

PADRAO_PDF = re.compile(r"REC-[0-9]{6,}\.pdf")


def limpar_pdfs_antigos(simular=True):
    """
    Exclui PDFs REC-NNNNNN.pdf cuja data de EMISSÃO (gravada no
    banco) ultrapassou o período de retenção.

    Regras de segurança (iguais às da versão 2.1.2):
    - somente arquivos no padrão REC-<número>.pdf;
    - ignora links simbólicos e itens que não sejam arquivos;
    - não exclui PDFs sem registro ou com data inválida;
    - os registros do banco NUNCA são apagados: o recibo pode
      ser gerado novamente a partir do histórico.

    Retorna um resumo com as quantidades.
    """

    resumo = {"antigos": 0, "excluidos": 0, "erros": 0}

    limite = datetime.now() - timedelta(days=DIAS_RETENCAO)

    if not PASTA_PDFS.exists():
        log.info("Pasta de PDFs não encontrada.")
        return resumo

    if not CAMINHO_BANCO.is_file():
        log.warning("Banco de dados não encontrado. Limpeza cancelada.")
        return resumo

    # Uma única conexão para toda a verificação
    with closing(sqlite3.connect(CAMINHO_BANCO, timeout=10)) as conexao:

        for arquivo in PASTA_PDFS.glob("REC-*.pdf"):

            # Verifica o padrão do arquivo
            if not PADRAO_PDF.fullmatch(arquivo.name):
                continue

            # Ignora links simbólicos
            if arquivo.is_symlink() or not arquivo.is_file():
                continue

            # Recupera o ID original do recibo
            numero_recibo = int(arquivo.stem[4:])

            try:
                resultado = conexao.execute(
                    "SELECT emitido_em FROM recibos WHERE id = ?",
                    (numero_recibo,)
                ).fetchone()

            except sqlite3.Error as erro:
                log.error("Erro ao consultar %s: %s", arquivo.name, erro)
                resumo["erros"] += 1
                continue

            # Não exclui PDFs sem registro correspondente
            if resultado is None or not resultado[0]:
                log.info("Sem data de emissão: %s", arquivo.name)
                continue

            try:
                data_arquivo = datetime.fromisoformat(resultado[0])

            except (ValueError, TypeError) as erro:
                log.warning("Data inválida em %s: %s", arquivo.name, erro)
                continue

            # Verifica se ultrapassou o prazo
            if data_arquivo >= limite:
                continue

            resumo["antigos"] += 1

            if simular:
                log.info("[SIMULAÇÃO] Excluiria: %s", arquivo.name)
                continue

            try:
                arquivo.unlink()
                resumo["excluidos"] += 1
                log.info("Excluído: %s", arquivo.name)

            except OSError as erro:
                # Ex.: PDF aberto em outro programa
                resumo["erros"] += 1
                log.warning("Erro ao excluir %s: %s", arquivo.name, erro)

    log.info(
        "Limpeza de PDFs: %d antigos, %d excluídos%s.",
        resumo["antigos"],
        resumo["excluidos"],
        " (simulação)" if simular else ""
    )

    return resumo


# Teste manual sem exclusão
if __name__ == "__main__":
    print(limpar_pdfs_antigos(simular=True))
