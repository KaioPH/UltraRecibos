
"""
Preferências de uso guardadas em dados/preferencias.json
(ex.: aparência clara/escura). Não contém dados de alunos.
"""

import json
import os

from caminhos import PASTA_DADOS


ARQUIVO_PREFERENCIAS = PASTA_DADOS / "preferencias.json"

PADROES = {
    "aparencia": "auto_horario",
}


def carregar_preferencias():

    dados = dict(PADROES)

    try:
        with open(ARQUIVO_PREFERENCIAS, "r", encoding="utf-8") as arquivo:
            salvo = json.load(arquivo)
        if isinstance(salvo, dict):
            dados.update({k: v for k, v in salvo.items() if k in PADROES})
    except (OSError, ValueError):
        # Arquivo inexistente ou danificado: usa os padrões
        pass

    return dados


def obter_preferencia(nome):

    return carregar_preferencias().get(nome, PADROES.get(nome))


def salvar_preferencia(nome, valor):

    if nome not in PADROES:
        raise ValueError(f"Preferência desconhecida: {nome}")

    dados = carregar_preferencias()
    dados[nome] = valor

    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    temporario = ARQUIVO_PREFERENCIAS.with_suffix(".json.tmp")

    try:
        with open(temporario, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=4)
        os.replace(temporario, ARQUIVO_PREFERENCIAS)
    finally:
        temporario.unlink(missing_ok=True)
