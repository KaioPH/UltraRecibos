
"""
Validações e formatações usadas pelo Ultra Recibos.

Funções puras (sem interface), para poderem ser testadas
automaticamente. As regras de CPF, valor, data e código de
autenticação são as mesmas da versão 2.1.2.
"""

import re

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from configuracoes import AUTENTICACAO_MIN, AUTENTICACAO_MAX


# =========================================
# CPF
# =========================================

def somente_digitos(texto):

    return re.sub(r"\D", "", str(texto or ""))


def validar_cpf(cpf):

    # Remove pontuação e espaços
    cpf = re.sub(r"[.\-\s]", "", str(cpf or ""))

    # Exige exatamente 11 dígitos
    if not re.fullmatch(r"[0-9]{11}", cpf):
        return False

    # Rejeita sequências repetidas
    if cpf == cpf[0] * 11:
        return False

    # Primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = (soma * 10) % 11

    if digito1 == 10:
        digito1 = 0

    # Segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = (soma * 10) % 11

    if digito2 == 10:
        digito2 = 0

    return int(cpf[9]) == digito1 and int(cpf[10]) == digito2


def mascarar_cpf(texto):
    """
    Aplica a máscara 000.000.000-00 enquanto se digita.
    """

    numeros = somente_digitos(texto)[:11]

    if len(numeros) > 9:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"

    if len(numeros) > 6:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:]}"

    if len(numeros) > 3:
        return f"{numeros[:3]}.{numeros[3:]}"

    return numeros


def formatar_cpf(cpf):
    """
    Exibe um CPF armazenado (11 dígitos) com pontuação.
    Outros conteúdos são devolvidos sem alteração.
    """

    cpf = str(cpf or "").strip()

    if re.fullmatch(r"[0-9]{11}", cpf):
        return mascarar_cpf(cpf)

    return cpf


# =========================================
# VALOR MONETÁRIO
# =========================================

def validar_valor(valor):

    valor = str(valor or "").strip()

    padrao = (
        r"(?:[0-9]+|[0-9]{1,3}"
        r"(?:\.[0-9]{3})+)"
        r"(?:,[0-9]{1,2})?"
    )

    if not re.fullmatch(padrao, valor):
        return None

    valor = valor.replace(".", "").replace(",", ".")

    try:
        valor_decimal = Decimal(valor)
    except InvalidOperation:
        return None

    if valor_decimal <= 0:
        return None

    return valor_decimal


def valor_para_centavos(valor_decimal):

    return int(valor_decimal * 100)


def formatar_reais(centavos):

    centavos = int(centavos)

    reais = centavos // 100
    centavos_restantes = centavos % 100

    reais_formatados = f"{reais:,}".replace(",", ".")

    return f"R$ {reais_formatados},{centavos_restantes:02d}"


def normalizar_valor_digitado(texto):
    """
    Ao sair do campo, padroniza o valor com duas casas
    (ex.: "9,9" -> "9,90"). Valores inválidos ficam
    como foram digitados para a validação apontar o erro.
    """

    valor = validar_valor(texto)

    if valor is None:
        return texto

    return formatar_reais(valor_para_centavos(valor))[3:]


# =========================================
# DATA
# =========================================

def validar_data(data_texto):

    data_texto = str(data_texto or "").strip()

    if not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", data_texto):
        return None

    try:
        data_convertida = datetime.strptime(data_texto, "%d/%m/%Y").date()
    except ValueError:
        return None

    # Não aceita datas futuras
    if data_convertida > date.today():
        return None

    return data_convertida


def mascarar_data(texto):

    numeros = somente_digitos(texto)[:8]

    if len(numeros) > 4:
        return f"{numeros[:2]}/{numeros[2:4]}/{numeros[4:]}"

    if len(numeros) > 2:
        return f"{numeros[:2]}/{numeros[2:]}"

    return numeros


# =========================================
# CÓDIGO DE AUTENTICAÇÃO DO PAGAMENTO
# =========================================

def filtrar_autenticacao(texto):
    """
    Mantém apenas letras e números, até o limite máximo.
    Zeros à esquerda e maiúsculas/minúsculas são preservados.
    """

    return re.sub(r"[^A-Za-z0-9]", "", str(texto or ""))[:AUTENTICACAO_MAX]


def validar_autenticacao(codigo):

    return bool(
        re.fullmatch(
            rf"[A-Za-z0-9]{{{AUTENTICACAO_MIN},{AUTENTICACAO_MAX}}}",
            str(codigo or "")
        )
    )


# =========================================
# CNPJ (NUMÉRICO E ALFANUMÉRICO)
# =========================================
# Desde julho de 2026 a Receita Federal emite CNPJ
# alfanumérico: 12 posições com 0-9/A-Z e 2 dígitos
# verificadores numéricos (módulo 11, valor = ASCII - 48).
# O cálculo é idêntico ao antigo para CNPJs só numéricos.

def normalizar_cnpj(cnpj):

    return re.sub(r"[^0-9A-Za-z]", "", str(cnpj or "")).upper()


def validar_cnpj(cnpj):

    cnpj = normalizar_cnpj(cnpj)

    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", cnpj):
        return False

    if cnpj == cnpj[0] * 14:
        return False

    def digito(base):
        # Pesos de 2 a 9, aplicados da direita para a esquerda
        pesos = [2 + i % 8 for i in range(len(base))][::-1]
        soma = sum((ord(c) - 48) * p for c, p in zip(base, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    dv1 = digito(cnpj[:12])
    dv2 = digito(cnpj[:12] + str(dv1))

    return cnpj[12:] == f"{dv1}{dv2}"


def formatar_cnpj(cnpj):

    cnpj = normalizar_cnpj(cnpj)

    if len(cnpj) != 14:
        return str(cnpj)

    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


# =========================================
# PESQUISA (LIKE)
# =========================================

def escapar_like(termo):
    """
    Impede que %, _ e \\ digitados sejam tratados
    como curingas na pesquisa do SQLite.
    """

    return (
        str(termo)
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
