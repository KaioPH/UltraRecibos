
import os
import shutil
import sqlite3
import tempfile

from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from caminhos import CAMINHO_BANCO, PASTA_DADOS, PASTA_BACKUPS
from registro import obter_logger


log = obter_logger("backup")


# Quantidade de dias de backups diários mantidos.
# Cada backup é uma cópia COMPLETA do banco (todos os recibos);
# apagar backups antigos não apaga nenhum recibo.
DIAS_BACKUPS = 90

# Arquivos de configuração copiados junto com o banco
ARQUIVOS_CONFIGURACAO = (
    "empresa.json",
    "logo_empresa.png"
)


def criar_backup():
    """
    Cria (ou atualiza) o backup do dia: backup_recibos_AAAAMMDD.db.

    A cópia usa a API de backup do SQLite (consistente mesmo
    com o banco em uso), passa por verificação de integridade e
    só então substitui o arquivo do dia.

    Também copia empresa.json e o logotipo personalizado para
    backups/configuracao_AAAAMMDD/.
    """

    if not CAMINHO_BANCO.is_file():
        log.warning("Banco de dados não encontrado para backup.")
        return None

    PASTA_BACKUPS.mkdir(
        parents=True,
        exist_ok=True
    )

    # Um arquivo de backup por dia
    data_atual = date.today().strftime("%Y%m%d")

    destino = PASTA_BACKUPS / f"backup_recibos_{data_atual}.db"

    temporario = None

    try:
        # Cria um arquivo temporário na mesma pasta
        with tempfile.NamedTemporaryFile(
            prefix="backup_temp_",
            suffix=".db",
            dir=PASTA_BACKUPS,
            delete=False
        ) as arquivo:
            temporario = Path(arquivo.name)

        # Faz uma cópia consistente do SQLite
        with closing(sqlite3.connect(CAMINHO_BANCO, timeout=10)) as origem:
            with closing(sqlite3.connect(temporario)) as copia:
                origem.backup(copia)

        # Verifica a integridade da cópia
        with closing(sqlite3.connect(temporario)) as conexao:
            resultado = conexao.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

        if resultado != "ok":
            raise RuntimeError(
                f"Falha na integridade: {resultado}"
            )

        # Substitui o backup diário somente
        # depois de concluir a cópia corretamente
        os.replace(temporario, destino)
        temporario = None

        _copiar_configuracao(data_atual)

        log.info("Backup atualizado: %s", destino.name)

        aplicar_retencao()

        return destino

    except Exception as erro:

        log.error("Erro ao criar backup: %s", erro)

        return None

    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


def _copiar_configuracao(data_atual):
    """
    Copia os arquivos de configuração da empresa.
    Falhas aqui não invalidam o backup do banco.
    """

    pasta = PASTA_BACKUPS / f"configuracao_{data_atual}"

    try:
        for nome in ARQUIVOS_CONFIGURACAO:

            origem = PASTA_DADOS / nome

            if origem.is_file():
                pasta.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origem, pasta / nome)

    except OSError as erro:
        log.warning("Configuração não copiada no backup: %s", erro)


def listar_backups():
    """
    Backups diários existentes, do mais recente ao mais antigo.
    """

    if not PASTA_BACKUPS.is_dir():
        return []

    return sorted(
        PASTA_BACKUPS.glob("backup_recibos_*.db"),
        reverse=True
    )


def ultimo_backup():
    """
    Retorna (caminho, data/hora da última gravação) ou None.
    """

    backups = listar_backups()

    if not backups:
        return None

    arquivo = backups[0]

    return arquivo, datetime.fromtimestamp(arquivo.stat().st_mtime)


# =========================================
# RETENÇÃO: ÚLTIMOS 90 BACKUPS DIÁRIOS
# =========================================

def aplicar_retencao(dias=DIAS_BACKUPS, hoje=None):
    """
    Remove backups diários (backup_recibos_AAAAMMDD.db e
    configuracao_AAAAMMDD) com mais de "dias" dias.

    Nunca remove as cópias de segurança automáticas
    antes_migracao_* e antes_restauracao_*.
    """

    hoje = hoje or date.today()
    limite = hoje - timedelta(days=dias)
    removidos = 0

    if not PASTA_BACKUPS.is_dir():
        return 0

    for item in PASTA_BACKUPS.iterdir():

        if item.name.startswith("backup_recibos_") and item.suffix == ".db":
            texto_data = item.stem[-8:]
        elif item.name.startswith("configuracao_") and item.is_dir():
            texto_data = item.name[-8:]
        else:
            continue

        try:
            data_item = datetime.strptime(texto_data, "%Y%m%d").date()
        except ValueError:
            continue

        if data_item >= limite:
            continue

        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            removidos += 1
        except OSError as erro:
            log.warning("Backup antigo não removido (%s): %s", item.name, erro)

    if removidos:
        log.info("Backups antigos removidos: %d", removidos)

    return removidos


# =========================================
# RESTAURAÇÃO
# =========================================

COLUNAS_OBRIGATORIAS = {
    "id", "nome", "cpf", "codigo_aluno", "plano", "valor_centavos",
    "forma_pagamento", "data_pagamento", "consultor", "emitido_em"
}


def inspecionar_backup(caminho, verificar_integridade=False):
    """
    Lê informações de um arquivo de backup sem alterá-lo.
    Lança ValueError se não for um banco do Ultra Recibos.
    """

    caminho = Path(caminho)

    if not caminho.is_file():
        raise ValueError("Arquivo de backup não encontrado.")

    try:
        uri = f"{caminho.resolve().as_uri()}?mode=ro"
        with closing(sqlite3.connect(uri, uri=True, timeout=10)) as conexao:

            colunas = {c[1] for c in conexao.execute("PRAGMA table_info(recibos)")}

            if not COLUNAS_OBRIGATORIAS <= colunas:
                raise ValueError(
                    "Este arquivo não é um banco de dados do Ultra Recibos."
                )

            total, ultimo, ultima_emissao = conexao.execute(
                "SELECT COUNT(*), MAX(id), MAX(emitido_em) FROM recibos"
            ).fetchone()

            integro = None

            if verificar_integridade:
                integro = conexao.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0] == "ok"

    except sqlite3.DatabaseError as erro:
        raise ValueError(
            f"Arquivo inválido ou danificado: {erro}"
        ) from erro

    return {
        "caminho": caminho,
        "total_recibos": total,
        "ultimo_id": ultimo or 0,
        "ultima_emissao": ultima_emissao,
        "tamanho_bytes": caminho.stat().st_size,
        "modificado_em": datetime.fromtimestamp(caminho.stat().st_mtime),
        "integro": integro,
    }


def restaurar_backup(caminho, restaurar_configuracao=False):
    """
    Substitui o banco atual pelo backup escolhido.

    1. Confere a integridade do backup.
    2. Salva o banco atual em backups/antes_restauracao_AAAAMMDD_HHMMSS.db
       (permite desfazer).
    3. Copia o backup para o banco em uso (API de backup do SQLite).
    4. Atualiza a estrutura, se o backup for de uma versão anterior.

    Retorna o caminho da cópia do banco anterior.
    """

    from caminhos import PASTA_DADOS

    caminho = Path(caminho)
    info = inspecionar_backup(caminho, verificar_integridade=True)

    if not info["integro"]:
        raise ValueError(
            "O backup escolhido está danificado e não pode ser restaurado."
        )

    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)

    # Nome único (nunca sobrescreve outro arquivo, inclusive o
    # próprio backup escolhido, caso seja uma cópia anterior)
    base = f"antes_restauracao_{datetime.now():%Y%m%d_%H%M%S}"
    copia_atual = PASTA_BACKUPS / f"{base}.db"
    contador = 1
    while copia_atual.exists():
        copia_atual = PASTA_BACKUPS / f"{base}_{contador}.db"
        contador += 1

    # 2. Guarda o banco atual
    if CAMINHO_BANCO.is_file():
        with closing(sqlite3.connect(CAMINHO_BANCO, timeout=10)) as atual:
            with closing(sqlite3.connect(copia_atual)) as destino:
                atual.backup(destino)

        log.info("Banco atual guardado em %s", copia_atual.name)

    # 3. Copia o backup para o banco em uso
    uri = f"{caminho.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=10)) as origem:
        with closing(sqlite3.connect(CAMINHO_BANCO, timeout=10)) as banco:
            origem.backup(banco)

    # Configuração da empresa do mesmo dia (backups internos)
    if restaurar_configuracao:
        pasta_config = PASTA_BACKUPS / f"configuracao_{caminho.stem[-8:]}"
        if pasta_config.is_dir():
            for nome in ARQUIVOS_CONFIGURACAO:
                origem_config = pasta_config / nome
                if origem_config.is_file():
                    shutil.copy2(origem_config, PASTA_DADOS / nome)

    # 4. Ajusta a estrutura (migrações) e tabelas auxiliares
    from database import criar_banco
    from consultores import inicializar_consultores
    from opcoes import inicializar_opcoes

    criar_banco()
    inicializar_consultores()
    inicializar_opcoes()

    log.info(
        "Backup restaurado: %s (%d recibos)",
        caminho.name, info["total_recibos"]
    )

    return copia_atual


def configuracao_do_backup(caminho):
    """
    Pasta de configuração (empresa/logo) do mesmo dia, se existir.
    """

    pasta = PASTA_BACKUPS / f"configuracao_{Path(caminho).stem[-8:]}"
    return pasta if pasta.is_dir() else None


if __name__ == "__main__":
    print(criar_backup())
