
"""
Planos e formas de pagamento editáveis (Configurações > Planos e pagamentos).

- Na primeira execução, a tabela é preenchida com as mesmas opções
  que eram fixas no código (configuracoes.py).
- "Desativar" esconde a opção do formulário, mas os recibos antigos
  continuam com o nome gravado (o recibo guarda o texto, não um código).
- Formas de pagamento têm a marcação "exige autenticação".
"""

import sqlite3

from configuracoes import PLANOS, FORMAS_PAGAMENTO, PAGAMENTOS_COM_AUTENTICACAO
from database import conectar


TIPOS = ("plano", "pagamento")


def inicializar_opcoes():

    with conectar() as conexao:

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS opcoes_formulario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL CHECK (tipo IN ('plano', 'pagamento')),
                nome TEXT NOT NULL COLLATE NOCASE,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                exige_autenticacao INTEGER NOT NULL DEFAULT 0
                    CHECK (exige_autenticacao IN (0, 1)),
                ordem INTEGER NOT NULL DEFAULT 0,
                UNIQUE (tipo, nome)
            )
        """)

        total, = conexao.execute(
            "SELECT COUNT(*) FROM opcoes_formulario"
        ).fetchone()

        if total == 0:

            conexao.executemany(
                "INSERT INTO opcoes_formulario (tipo, nome, ordem) VALUES ('plano', ?, ?)",
                [(nome, i) for i, nome in enumerate(PLANOS)]
            )

            conexao.executemany(
                "INSERT INTO opcoes_formulario "
                "(tipo, nome, ordem, exige_autenticacao) VALUES ('pagamento', ?, ?, ?)",
                [
                    (nome, i, int(nome in PAGAMENTOS_COM_AUTENTICACAO))
                    for i, nome in enumerate(FORMAS_PAGAMENTO)
                ]
            )


def listar_opcoes(tipo, apenas_ativas=True):
    """
    Retorna linhas (id, nome, ativo, exige_autenticacao) na ordem cadastrada.
    """

    _validar_tipo(tipo)

    consulta = (
        "SELECT id, nome, ativo, exige_autenticacao "
        "FROM opcoes_formulario WHERE tipo = ?"
    )

    if apenas_ativas:
        consulta += " AND ativo = 1"

    consulta += " ORDER BY ordem, id"

    with conectar() as conexao:
        return conexao.execute(consulta, (tipo,)).fetchall()


def nomes_ativos(tipo):

    return [linha[1] for linha in listar_opcoes(tipo)]


def pagamentos_com_autenticacao():

    return {
        nome
        for _id, nome, ativo, exige in listar_opcoes("pagamento", apenas_ativas=False)
        if exige
    }


def adicionar_opcao(tipo, nome, exige_autenticacao=False):

    _validar_tipo(tipo)
    nome = _normalizar(nome)

    try:
        with conectar() as conexao:

            proxima, = conexao.execute(
                "SELECT COALESCE(MAX(ordem), -1) + 1 FROM opcoes_formulario WHERE tipo = ?",
                (tipo,)
            ).fetchone()

            conexao.execute(
                "INSERT INTO opcoes_formulario (tipo, nome, ordem, exige_autenticacao) "
                "VALUES (?, ?, ?, ?)",
                (tipo, nome, proxima, int(bool(exige_autenticacao)))
            )

    except sqlite3.IntegrityError as erro:
        raise ValueError("Essa opção já está cadastrada.") from erro


def renomear_opcao(id_opcao, novo_nome):

    novo_nome = _normalizar(novo_nome)

    try:
        with conectar() as conexao:
            cursor = conexao.execute(
                "UPDATE opcoes_formulario SET nome = ? WHERE id = ?",
                (novo_nome, id_opcao)
            )
            if cursor.rowcount == 0:
                raise ValueError("Opção não encontrada.")

    except sqlite3.IntegrityError as erro:
        raise ValueError("Já existe uma opção com esse nome.") from erro


def alterar_status_opcao(id_opcao, ativo):

    with conectar() as conexao:

        if not ativo:
            tipo, = conexao.execute(
                "SELECT tipo FROM opcoes_formulario WHERE id = ?", (id_opcao,)
            ).fetchone() or (None,)

            ativos, = conexao.execute(
                "SELECT COUNT(*) FROM opcoes_formulario WHERE tipo = ? AND ativo = 1",
                (tipo,)
            ).fetchone()

            if ativos <= 1:
                raise ValueError("Mantenha pelo menos uma opção ativa.")

        cursor = conexao.execute(
            "UPDATE opcoes_formulario SET ativo = ? WHERE id = ?",
            (int(bool(ativo)), id_opcao)
        )

        if cursor.rowcount == 0:
            raise ValueError("Opção não encontrada.")


def alterar_autenticacao(id_opcao, exige):

    with conectar() as conexao:
        conexao.execute(
            "UPDATE opcoes_formulario SET exige_autenticacao = ? "
            "WHERE id = ? AND tipo = 'pagamento'",
            (int(bool(exige)), id_opcao)
        )


def mover_opcao(id_opcao, direcao):
    """
    direcao: -1 sobe, +1 desce (troca a posição com a vizinha).
    """

    with conectar() as conexao:

        tipo, = conexao.execute(
            "SELECT tipo FROM opcoes_formulario WHERE id = ?", (id_opcao,)
        ).fetchone()

        ids = [
            linha[0] for linha in conexao.execute(
                "SELECT id FROM opcoes_formulario WHERE tipo = ? ORDER BY ordem, id",
                (tipo,)
            )
        ]

        i = ids.index(id_opcao)
        j = i + direcao

        if not 0 <= j < len(ids):
            return

        ids[i], ids[j] = ids[j], ids[i]

        conexao.executemany(
            "UPDATE opcoes_formulario SET ordem = ? WHERE id = ?",
            [(posicao, identificador) for posicao, identificador in enumerate(ids)]
        )


def _normalizar(nome):

    nome = " ".join(str(nome or "").split())

    if len(nome) < 2:
        raise ValueError("Informe um nome com pelo menos 2 caracteres.")

    if len(nome) > 40:
        raise ValueError("Use no máximo 40 caracteres.")

    return nome


def _validar_tipo(tipo):

    if tipo not in TIPOS:
        raise ValueError(f"Tipo inválido: {tipo}")
