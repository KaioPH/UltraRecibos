
import hashlib
import os
import re
import secrets
import sqlite3

from database import conectar

from seguranca_admin import (
    ITERACOES,
    autenticar_admin,
    gerar_hash_senha,
    inicializar_seguranca
)


# =========================================
# BANCO DE CÓDIGOS DE RECUPERAÇÃO
# =========================================

def inicializar_recuperacao():

    inicializar_seguranca()

    with conectar() as conexao:

        conexao.execute("""
            CREATE TABLE IF NOT EXISTS codigos_recuperacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                codigo_hash TEXT NOT NULL UNIQUE
            )
        """)


# =========================================
# VALIDAÇÃO DOS CÓDIGOS
# =========================================

def normalizar_codigo(codigo):

    codigo = re.sub(
        r"[\s-]",
        "",
        str(codigo)
    ).upper()

    if not re.fullmatch(r"[0-9A-F]{32}", codigo):
        raise ValueError(
            "Código de recuperação inválido."
        )

    return codigo


def hash_codigo(codigo):

    codigo = normalizar_codigo(codigo)

    conteudo = (
        "ultrarecibos:recuperacao:v1:"
        + codigo
    )

    return hashlib.sha256(
        conteudo.encode("ascii")
    ).hexdigest()


# =========================================
# GERAR SEIS CÓDIGOS DE RECUPERAÇÃO
# =========================================

def gerar_codigos_recuperacao(usuario, senha):

    inicializar_recuperacao()

    usuario = usuario.strip().lower()

    # Exige a senha atual do administrador
    if not autenticar_admin(usuario, senha):
        raise PermissionError(
            "Credenciais administrativas inválidas."
        )

    codigos = []

    with conectar() as conexao:

        registro = conexao.execute(
            """
            SELECT id
            FROM usuarios_admin
            WHERE usuario = ?
              AND ativo = 1
            """,
            (usuario,)
        ).fetchone()

        if registro is None:
            raise ValueError(
                "Administrador não encontrado."
            )

        usuario_id = registro[0]

        # Invalida códigos anteriores
        conexao.execute(
            """
            DELETE FROM codigos_recuperacao
            WHERE usuario_id = ?
            """,
            (usuario_id,)
        )

        for _ in range(6):

            # 128 bits gerados com fonte
            # criptograficamente segura
            codigo = secrets.token_hex(16).upper()

            conexao.execute(
                """
                INSERT INTO codigos_recuperacao
                (usuario_id, codigo_hash)
                VALUES (?, ?)
                """,
                (
                    usuario_id,
                    hash_codigo(codigo)
                )
            )

            # Formatação para facilitar a leitura
            codigo_formatado = "-".join(
                codigo[i:i + 8]
                for i in range(0, 32, 8)
            )

            codigos.append(codigo_formatado)

    # Exibir apenas uma vez na interface
    return codigos


# =========================================
# RECUPERAR USUÁRIO E SENHA
# =========================================

def recuperar_acesso(
    codigo,
    novo_usuario,
    nova_senha
):

    inicializar_recuperacao()

    novo_usuario = novo_usuario.strip().lower()

    if not re.fullmatch(
        r"[a-z0-9_.-]{3,32}",
        novo_usuario
    ):
        raise ValueError(
            "O usuário deve ter de 3 a 32 "
            "caracteres válidos."
        )

    if len(nova_senha) < 6:
        raise ValueError(
            "A senha precisa ter pelo menos "
            "6 caracteres."
        )

    codigo_verificacao = hash_codigo(codigo)

    salt = os.urandom(16)

    nova_hash = gerar_hash_senha(
        nova_senha,
        salt,
        ITERACOES
    )

    try:

        with conectar() as conexao:

            # Impede duas recuperações simultâneas
            conexao.execute("BEGIN IMMEDIATE")

            registro = conexao.execute(
                """
                SELECT c.usuario_id
                FROM codigos_recuperacao AS c
                JOIN usuarios_admin AS a
                  ON a.id = c.usuario_id
                WHERE c.codigo_hash = ?
                  AND a.ativo = 1
                """,
                (codigo_verificacao,)
            ).fetchone()

            if registro is None:
                raise ValueError(
                    "Código inválido ou já utilizado."
                )

            usuario_id = registro[0]

            # Redefine usuário e senha
            conexao.execute(
                """
                UPDATE usuarios_admin
                SET usuario = ?,
                    senha_hash = ?,
                    senha_salt = ?,
                    iteracoes = ?
                WHERE id = ?
                  AND ativo = 1
                """,
                (
                    novo_usuario,
                    nova_hash,
                    salt,
                    ITERACOES,
                    usuario_id
                )
            )

            # Invalida todos os códigos anteriores
            # do administrador recuperado
            conexao.execute(
                """
                DELETE FROM codigos_recuperacao
                WHERE usuario_id = ?
                """,
                (usuario_id,)
            )

    except sqlite3.IntegrityError as erro:

        raise ValueError(
            "O nome de usuário escolhido "
            "já está em uso."
        ) from erro

    return True


# =========================================
# INICIALIZAÇÃO
# =========================================

if __name__ == "__main__":

    inicializar_recuperacao()

    print(
        "Sistema de recuperação inicializado."
    )
