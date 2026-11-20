
import hashlib
import sqlite3

from contextlib import contextmanager
from datetime import datetime, timedelta

from caminhos import PASTA_DADOS, CAMINHO_BANCO
from configuracoes import DIAS_RETENCAO, HORAS_HISTORICO_INICIAL
from empresa_config import obter_logo_empresa
from registro import obter_logger
from validacoes import escapar_like


log = obter_logger("database")


# =========================================
# CONEXÃO PADRÃO COM O SQLITE
# =========================================

@contextmanager
def conectar(row_factory=None):
    """
    Abre o banco, confirma (commit) as alterações ao final,
    desfaz (rollback) em caso de erro e SEMPRE fecha a conexão.

    Fechar a conexão é importante no Windows, onde um arquivo
    aberto não pode ser substituído nem copiado com segurança.
    """

    conexao = sqlite3.connect(CAMINHO_BANCO, timeout=10)

    try:
        if row_factory is not None:
            conexao.row_factory = row_factory

        with conexao:
            yield conexao

    finally:
        conexao.close()


# =========================================
# FUNÇÃO PARA CRIAR O BANCO DE DADOS
# =========================================

def criar_banco():

    # Cria a pasta de armazenamento
    PASTA_DADOS.mkdir(
        parents=True,
        exist_ok=True
    )

    with conectar() as conexao:

        # Cria a tabela de recibos
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS recibos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cpf TEXT NOT NULL,
                codigo_aluno TEXT NOT NULL,
                plano TEXT NOT NULL,
                valor_centavos INTEGER NOT NULL,
                forma_pagamento TEXT NOT NULL,
                data_pagamento TEXT NOT NULL,
                consultor TEXT NOT NULL,
                emitido_em TEXT NOT NULL
            )
        """)

        # Migrações: colunas adicionadas nas versões 2.x
        colunas = {
            linha[1]
            for linha in conexao.execute(
                "PRAGMA table_info(recibos)"
            )
        }

        novas_colunas = {
            # Logotipo original de cada recibo
            "emissor_logo": "BLOB",
            # Empresa emissora no momento da emissão
            "emissor_razao_social": "TEXT",
            "emissor_cnpj": "TEXT",
            "emissor_cidade": "TEXT",
            # Autenticação do pagamento (texto: preserva zeros)
            "codigo_autenticacao": "TEXT",
            # 2.3.0: referência ao logotipo na tabela "logos"
            "emissor_logo_hash": "TEXT"
        }

        for nome_coluna, tipo in novas_colunas.items():

            if nome_coluna not in colunas:

                conexao.execute(
                    f"ALTER TABLE recibos "
                    f"ADD COLUMN {nome_coluna} {tipo}"
                )

                log.info("Coluna adicionada: %s", nome_coluna)

        # 2.3.0: cada logotipo é guardado uma única vez
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS logos (
                hash TEXT PRIMARY KEY,
                imagem BLOB NOT NULL
            )
        """)

        # 2.3.0: acelera o histórico (filtro pelos últimos 90 dias)
        conexao.execute(
            "CREATE INDEX IF NOT EXISTS idx_recibos_emitido_em "
            "ON recibos (emitido_em)"
        )

    migrar_logos()


# =========================================
# MIGRAÇÃO 2.3.0: LOGOTIPOS SEM REPETIÇÃO
# =========================================

def hash_logo(dados):

    return hashlib.sha256(dados).hexdigest()


def migrar_logos():
    """
    Move as cópias do logotipo gravadas em cada recibo
    (coluna emissor_logo) para a tabela "logos", guardando
    cada imagem uma única vez. A imagem de cada recibo
    continua exatamente a mesma (conferida pelo hash).

    Antes da primeira migração é feita uma cópia completa
    do banco em backups/antes_migracao_logos_AAAAMMDD_HHMMSS.db.
    """

    with conectar() as conexao:
        pendentes, = conexao.execute(
            "SELECT COUNT(*) FROM recibos "
            "WHERE emissor_logo IS NOT NULL"
        ).fetchone()

    if not pendentes:
        return 0

    _copia_antes_da_migracao()

    with conectar() as conexao:

        conexao.execute("BEGIN IMMEDIATE")

        registros = conexao.execute(
            "SELECT id, emissor_logo FROM recibos "
            "WHERE emissor_logo IS NOT NULL"
        ).fetchall()

        for id_recibo, imagem in registros:

            codigo = hash_logo(imagem)

            conexao.execute(
                "INSERT OR IGNORE INTO logos (hash, imagem) VALUES (?, ?)",
                (codigo, imagem)
            )

            # Confere se a imagem gravada é idêntica antes de liberar
            gravada, = conexao.execute(
                "SELECT imagem FROM logos WHERE hash = ?", (codigo,)
            ).fetchone()

            if bytes(gravada) != bytes(imagem):
                raise RuntimeError("Falha na conferência do logotipo.")

            conexao.execute(
                "UPDATE recibos SET emissor_logo_hash = ?, "
                "emissor_logo = NULL WHERE id = ?",
                (codigo, id_recibo)
            )

    # Devolve ao disco o espaço liberado
    conexao_vacuum = sqlite3.connect(CAMINHO_BANCO, timeout=10)
    try:
        conexao_vacuum.execute("VACUUM")
    finally:
        conexao_vacuum.close()

    log.info("Logotipos migrados: %d recibo(s).", len(registros))

    return len(registros)


def _copia_antes_da_migracao():

    from caminhos import PASTA_BACKUPS

    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)

    destino = PASTA_BACKUPS / (
        f"antes_migracao_logos_{datetime.now():%Y%m%d_%H%M%S}.db"
    )

    origem = sqlite3.connect(CAMINHO_BANCO, timeout=10)
    copia = sqlite3.connect(destino)

    try:
        origem.backup(copia)
    finally:
        copia.close()
        origem.close()

    log.info("Cópia antes da migração: %s", destino.name)


# =========================================
# SALVAR RECIBO COM DADOS DA EMPRESA
# =========================================

def inserir_recibo(
    nome,
    cpf,
    codigo_aluno,
    plano,
    valor_centavos,
    forma_pagamento,
    data_pagamento,
    consultor,
    codigo_autenticacao=None
):

    from configuracoes import (
        RAZAO_SOCIAL,
        CNPJ_EMPRESA,
        CIDADE_EMPRESA
    )

    # Carrega os dados definidos em Configurações
    from empresa_config import carregar_empresa

    empresa_atual = carregar_empresa()

    # Mantém os dados originais enquanto
    # nenhuma personalização tiver sido salva.
    if empresa_atual is None:
        empresa_atual = {
            "razao_social": RAZAO_SOCIAL,
            "cnpj": CNPJ_EMPRESA,
            "cidade": CIDADE_EMPRESA
        }

    # Registra data e hora da emissão
    emitido_em = datetime.now().isoformat(
        timespec="seconds"
    )

    # Logotipo utilizado no momento da emissão
    caminho_logo = obter_logo_empresa()
    logo_bytes = (
        caminho_logo.read_bytes()
        if caminho_logo is not None
        else None
    )
    logo_hash = hash_logo(logo_bytes) if logo_bytes else None

    # Registra recibo, empresa e logotipo na mesma transação
    with conectar() as conexao:

        # Guarda a imagem uma única vez
        if logo_hash is not None:
            conexao.execute(
                "INSERT OR IGNORE INTO logos (hash, imagem) VALUES (?, ?)",
                (logo_hash, logo_bytes)
            )

        cursor = conexao.execute(
            """
            INSERT INTO recibos (
                nome,
                cpf,
                codigo_aluno,
                plano,
                valor_centavos,
                forma_pagamento,
                data_pagamento,
                consultor,
                emitido_em,
                emissor_razao_social,
                emissor_cnpj,
                emissor_cidade,
                codigo_autenticacao,
                emissor_logo_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                cpf,
                codigo_aluno,
                plano,
                valor_centavos,
                forma_pagamento,
                data_pagamento,
                consultor,
                emitido_em,
                empresa_atual["razao_social"],
                empresa_atual["cnpj"],
                empresa_atual["cidade"],
                codigo_autenticacao,
                logo_hash
            )
        )

        id_recibo = cursor.lastrowid

    log.info("Recibo REC-%06d registrado.", id_recibo)

    return id_recibo


# =========================================
# HISTÓRICO DE RECIBOS - 90 DIAS
# =========================================

def _data_limite_historico():

    return (
        datetime.now() - timedelta(days=DIAS_RETENCAO)
    ).isoformat(timespec="seconds")


# Colunas exibidas no histórico (sem o logotipo,
# que pode ser grande e não é necessário na lista)
_COLUNAS_LISTA = """
    id, nome, cpf, codigo_aluno, plano, valor_centavos,
    forma_pagamento, data_pagamento, consultor, emitido_em,
    codigo_autenticacao
"""


def pesquisar_recibos(termo):

    termo = str(termo or "").strip()

    if not termo:
        return []

    # Pesquisa por nome, CPF ou código do aluno
    busca = f"%{escapar_like(termo)}%"

    with conectar(sqlite3.Row) as conexao:

        return conexao.execute(
            f"""
            SELECT {_COLUNAS_LISTA}
            FROM recibos
            WHERE emitido_em >= ?
              AND (
                  nome LIKE ? ESCAPE '\\'
                  OR cpf LIKE ? ESCAPE '\\'
                  OR codigo_aluno LIKE ? ESCAPE '\\'
              )
            ORDER BY id DESC
            LIMIT 50
            """,
            (
                _data_limite_historico(),
                busca,
                busca,
                busca
            )
        ).fetchall()


def listar_recibos_recentes(limite=200, horas=HORAS_HISTORICO_INICIAL):
    """
    Recibos exibidos ao abrir o histórico: emitidos nas últimas
    48 horas (a pesquisa continua cobrindo 90 dias).
    """

    limite_data = (
        datetime.now() - timedelta(hours=horas)
    ).isoformat(timespec="seconds")

    with conectar(sqlite3.Row) as conexao:

        return conexao.execute(
            f"""
            SELECT {_COLUNAS_LISTA}
            FROM recibos
            WHERE emitido_em >= ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (limite_data, int(limite))
        ).fetchall()


# Função para recuperar um recibo pelo ID

def buscar_recibo_por_id(id_recibo):

    with conectar(sqlite3.Row) as conexao:

        return conexao.execute(
            """
            SELECT r.*, l.imagem AS logo_imagem
            FROM recibos AS r
            LEFT JOIN logos AS l ON l.hash = r.emissor_logo_hash
            WHERE r.id = ?
            """,
            (id_recibo,)
        ).fetchone()


def buscar_duplicados(cpf, valor_centavos, data_pagamento):
    """
    Recibos do histórico com o mesmo CPF, valor e data de
    pagamento. Usado apenas para AVISAR; nunca impede o lançamento.
    """

    with conectar(sqlite3.Row) as conexao:

        return conexao.execute(
            """
            SELECT id, emitido_em, plano, forma_pagamento
            FROM recibos
            WHERE emitido_em >= ?
              AND cpf = ?
              AND valor_centavos = ?
              AND data_pagamento = ?
            ORDER BY id DESC
            LIMIT 5
            """,
            (_data_limite_historico(), cpf, int(valor_centavos), data_pagamento)
        ).fetchall()


def estatisticas_banco():
    """
    Informações para a aba Sistema das Configurações.
    """

    with conectar() as conexao:

        total, = conexao.execute(
            "SELECT COUNT(*) FROM recibos"
        ).fetchone()

        recentes, = conexao.execute(
            "SELECT COUNT(*) FROM recibos WHERE emitido_em >= ?",
            (_data_limite_historico(),)
        ).fetchone()

    tamanho = CAMINHO_BANCO.stat().st_size if CAMINHO_BANCO.exists() else 0

    return {
        "total_recibos": total,
        "recibos_periodo": recentes,
        "tamanho_bytes": tamanho
    }


# Executa quando abrimos este arquivo diretamente
if __name__ == "__main__":
    criar_banco()
    print("Banco de dados preparado.")
