
import json
import os
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from caminhos import PASTA_DADOS
from validacoes import normalizar_cnpj, validar_cnpj


# Logotipo: dimensão máxima armazenada (pixels).
# O recibo imprime o logo com 30 x 18 mm; 1200 px
# mantém ótima qualidade e evita bancos muito grandes,
# pois cada recibo guarda uma cópia do logotipo.
LOGO_DIMENSAO_MAXIMA = 1200


# =========================================
# ARQUIVO DE CONFIGURAÇÕES DA EMPRESA
# =========================================

ARQUIVO_EMPRESA = PASTA_DADOS / "empresa.json"


# =========================================
# CARREGAR EMPRESA CADASTRADA
# =========================================

def carregar_empresa():

    if not ARQUIVO_EMPRESA.exists():
        return None

    with open(
        ARQUIVO_EMPRESA,
        "r",
        encoding="utf-8"
    ) as arquivo:
        try:
            dados = json.load(arquivo)
        except json.JSONDecodeError as erro:
            raise ValueError(
                "O arquivo de configuração da empresa está "
                "danificado. Abra Configurações > Empresa, "
                "confira os dados e salve novamente."
            ) from erro

    if not isinstance(dados, dict):
        raise ValueError(
            "Arquivo de configuração da empresa inválido."
        )

    campos = (
        "razao_social",
        "cnpj",
        "cidade"
    )

    if any(
        not isinstance(dados.get(campo), str)
        or not dados[campo].strip()
        for campo in campos
    ):
        raise ValueError(
            "Configuração da empresa incompleta."
        )

    return dados


# =========================================
# SALVAR CONFIGURAÇÕES DA EMPRESA
# =========================================

def salvar_empresa(razao_social, cnpj, cidade):

    razao_social = razao_social.strip()
    cidade = cidade.strip()

    # Aceita CNPJ numérico ou alfanumérico (2026+)
    cnpj = normalizar_cnpj(cnpj)

    if not razao_social:
        raise ValueError(
            "Informe a razão social da empresa."
        )

    if len(cnpj) != 14:
        raise ValueError(
            "O CNPJ deve conter 14 caracteres."
        )

    if not validar_cnpj(cnpj):
        raise ValueError(
            "O CNPJ informado é inválido. "
            "Confira os dígitos verificadores."
        )

    if not cidade:
        raise ValueError(
            "Informe a cidade da empresa."
        )

    dados = {
        "razao_social": razao_social,
        "cnpj": cnpj,
        "cidade": cidade
    }

    PASTA_DADOS.mkdir(
        parents=True,
        exist_ok=True
    )

    arquivo_temporario = ARQUIVO_EMPRESA.with_suffix(
        ".json.tmp"
    )

    try:
        with open(
            arquivo_temporario,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                dados,
                arquivo,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            arquivo_temporario,
            ARQUIVO_EMPRESA
        )

    finally:
        arquivo_temporario.unlink(
            missing_ok=True
        )

    return dados


# =========================================
# LOGOTIPO PERSONALIZADO DA EMPRESA
# =========================================

ARQUIVO_LOGO = PASTA_DADOS / "logo_empresa.png"


def obter_logo_empresa():
    """
    Retorna o caminho do logotipo cadastrado.
    """
    if ARQUIVO_LOGO.is_file():
        return ARQUIVO_LOGO

    return None


def salvar_logo_empresa(caminho_origem):
    """
    Salva uma cópia do logotipo na pasta
    de dados do Ultra Recibos.
    """

    origem = Path(caminho_origem)

    if not origem.is_file():
        raise ValueError(
            "A imagem selecionada não existe."
        )

    if origem.stat().st_size > 10 * 1024 * 1024:
        raise ValueError(
            "A imagem deve ter no máximo 10 MB."
        )

    PASTA_DADOS.mkdir(
        parents=True,
        exist_ok=True
    )

    temporario = PASTA_DADOS / "logo_empresa.tmp.png"

    try:
        with Image.open(origem) as imagem:

            if imagem.format not in (
                "PNG",
                "JPEG",
                "WEBP"
            ):
                raise ValueError(
                    "Selecione uma imagem PNG, JPG ou WEBP."
                )

            if (
                imagem.width > 4000
                or imagem.height > 4000
            ):
                raise ValueError(
                    "A imagem deve ter no máximo "
                    "4000 pixels por dimensão."
                )

            imagem = imagem.convert("RGBA")

            # Reduz imagens grandes mantendo a proporção
            imagem.thumbnail(
                (LOGO_DIMENSAO_MAXIMA, LOGO_DIMENSAO_MAXIMA),
                Image.Resampling.LANCZOS
            )

            imagem.save(temporario, format="PNG", optimize=True)

        os.replace(
            temporario,
            ARQUIVO_LOGO
        )

    except (UnidentifiedImageError, OSError) as erro:
        raise ValueError(
            "Não foi possível processar a imagem."
        ) from erro

    finally:
        temporario.unlink(missing_ok=True)

    return ARQUIVO_LOGO


def remover_logo_empresa():
    """
    Remove o logotipo personalizado. Recibos já emitidos
    mantêm o logotipo que foi gravado no banco de dados.
    """

    ARQUIVO_LOGO.unlink(missing_ok=True)
