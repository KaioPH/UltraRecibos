
import hashlib
import hmac
import os
import re


from database import criar_banco, conectar


ITERACOES = 600_000


def inicializar_seguranca():

    criar_banco()

    with conectar() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS usuarios_admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash BLOB NOT NULL,
                senha_salt BLOB NOT NULL,
                iteracoes INTEGER NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1
            )
        """)


def gerar_hash_senha(senha, salt, iteracoes):

    return hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        iteracoes
    )


def cadastrar_primeiro_admin(usuario, senha):

    usuario = usuario.strip().lower()

    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", usuario):
        raise ValueError(
            "O usuário deve ter entre 3 e 32 caracteres, "
            "usando letras, números, ponto, hífen ou sublinhado."
        )

    if len(senha) < 6:
        raise ValueError(
            "A senha precisa ter pelo menos 6 caracteres."
        )

    inicializar_seguranca()

    salt = os.urandom(16)

    senha_hash = gerar_hash_senha(
        senha,
        salt,
        ITERACOES
    )

    with conectar() as conexao:

        conexao.execute("BEGIN IMMEDIATE")

        total = conexao.execute(
            "SELECT COUNT(*) FROM usuarios_admin"
        ).fetchone()[0]

        if total > 0:
            raise ValueError(
                "O administrador inicial já foi cadastrado."
            )

        conexao.execute(
            """
            INSERT INTO usuarios_admin
            (usuario, senha_hash, senha_salt, iteracoes)
            VALUES (?, ?, ?, ?)
            """,
            (
                usuario,
                senha_hash,
                salt,
                ITERACOES
            )
        )


def autenticar_admin(usuario, senha):

    usuario = usuario.strip().lower()

    with conectar() as conexao:

        registro = conexao.execute(
            """
            SELECT senha_hash, senha_salt, iteracoes
            FROM usuarios_admin
            WHERE usuario = ?
              AND ativo = 1
            """,
            (usuario,)
        ).fetchone()

    if registro is None:
        return False

    hash_armazenado, salt, iteracoes = registro

    hash_informado = gerar_hash_senha(
        senha,
        salt,
        iteracoes
    )

    return hmac.compare_digest(
        hash_informado,
        hash_armazenado
    )


if __name__ == "__main__":

    inicializar_seguranca()

    print(
        "Estrutura administrativa criada com sucesso."
    )
