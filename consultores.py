


import sqlite3

from database import criar_banco, conectar


# =========================================
# CONSULTORES INICIAIS
# =========================================

# Os nomes reais ficam em dados_locais.py (fora do Git).
# Sem esse arquivo, o programa usa os nomes de exemplo abaixo.
CONSULTORES_INICIAIS = [
    "Consultor Exemplo 1",
    "Consultor Exemplo 2",
    "Consultor Exemplo 3"
]

try:
    from dados_locais import CONSULTORES_INICIAIS
except ImportError:
    pass


# =========================================
# PREPARAR A TABELA
# =========================================

def inicializar_consultores():

    criar_banco()

    with conectar() as conexao:

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS consultores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
                ativo INTEGER NOT NULL DEFAULT 1
                    CHECK (ativo IN (0, 1))
            )
        """)

        total = conexao.execute(
            "SELECT COUNT(*) FROM consultores"
        ).fetchone()[0]

        if total == 0:

            conexao.executemany(
                """
                INSERT INTO consultores (nome, ativo)
                VALUES (?, 1)
                """,
                [(nome,) for nome in CONSULTORES_INICIAIS]
            )


# =========================================
# LISTAR CONSULTORES
# =========================================

def listar_consultores(apenas_ativos=True):

    consulta = """
        SELECT id, nome, ativo
        FROM consultores
    """

    if apenas_ativos:
        consulta += " WHERE ativo = 1"

    consulta += " ORDER BY nome COLLATE NOCASE"

    with conectar() as conexao:
        return conexao.execute(consulta).fetchall()


# =========================================
# CADASTRAR CONSULTOR
# =========================================

def cadastrar_consultor(nome):

    nome = " ".join(nome.strip().split())

    if len(nome) < 3:
        raise ValueError("Informe o nome do consultor.")

    try:
        with conectar() as conexao:

            conexao.execute(
                """
                INSERT INTO consultores (nome, ativo)
                VALUES (?, 1)
                """,
                (nome,)
            )

    except sqlite3.IntegrityError as erro:
        raise ValueError(
            "Já existe um consultor com este nome."
        ) from erro


# =========================================
# ALTERAR NOME DO CONSULTOR
# =========================================

def alterar_consultor(id_consultor, novo_nome):

    novo_nome = " ".join(novo_nome.strip().split())

    if len(novo_nome) < 3:
        raise ValueError("Informe um nome válido.")

    try:
        with conectar() as conexao:

            cursor = conexao.execute(
                """
                UPDATE consultores
                SET nome = ?
                WHERE id = ?
                """,
                (novo_nome, id_consultor)
            )

            if cursor.rowcount == 0:
                raise ValueError("Consultor não encontrado.")

    except sqlite3.IntegrityError as erro:
        raise ValueError(
            "Já existe um consultor com este nome."
        ) from erro


# =========================================
# ATIVAR OU DESATIVAR CONSULTOR
# =========================================

def alterar_status_consultor(id_consultor, ativo):

    with conectar() as conexao:

        cursor = conexao.execute(
            """
            UPDATE consultores
            SET ativo = ?
            WHERE id = ?
            """,
            (int(bool(ativo)), id_consultor)
        )

        if cursor.rowcount == 0:
            raise ValueError("Consultor não encontrado.")


# =========================================
# TESTE
# =========================================

if __name__ == "__main__":

    inicializar_consultores()

    print("\nCONSULTORES CADASTRADOS:\n")

    for id_consultor, nome, ativo in listar_consultores():

        print(f"{id_consultor} - {nome}")
