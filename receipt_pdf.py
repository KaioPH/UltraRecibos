
import os
import tempfile

from datetime import date
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO
from reportlab.lib.utils import ImageReader
from database import buscar_recibo_por_id
from caminhos import PASTA_PDFS
from registro import obter_logger
from validacoes import normalizar_cnpj, formatar_cpf, formatar_cnpj


log = obter_logger("pdf")


class PdfEmUsoError(OSError):
    """
    O PDF existente está aberto em outro programa
    (comum no Windows) e não pôde ser substituído.
    """


# =========================================
# 1. CONFIGURAÇÕES DO RECIBO
# =========================================

from configuracoes import (
    NOME_SOFTWARE,
    DESENVOLVEDOR,
    DESCRICAO_PADRAO,
    MOSTRAR_NUMERO_RECIBO
)



# =========================================
# 2. NOMES COMPLETOS DOS CONSULTORES
# =========================================

# Corrige a apresentação dos nomes antigos
# sem modificar os registros do SQLite.

# Os nomes reais ficam em dados_locais.py (fora do Git).
# Sem esse arquivo, nenhum nome antigo é convertido.
CONSULTORES_ANTIGOS = {}

try:
    from dados_locais import CONSULTORES_ANTIGOS
except ImportError:
    pass


# =========================================
# 3. FORMATAÇÃO MONETÁRIA
# =========================================

def formatar_valor(centavos):

    centavos = int(centavos)

    reais = centavos // 100
    centavos_restantes = centavos % 100

    reais_formatados = (
        f"{reais:,}".replace(",", ".")
    )

    return (
        f"R${reais_formatados},"
        f"{centavos_restantes:02d}"
    )


# =========================================
# 4. NOME COMPLETO DO CONSULTOR
# =========================================

def formatar_consultor(nome):

    nome = str(nome or "").strip()

    return CONSULTORES_ANTIGOS.get(
        nome.casefold(),
        nome
    )


# =========================================
# 5. AJUSTE AUTOMÁTICO DAS FONTES
# =========================================

def ajustar_fonte(
    conteudo,
    fonte,
    tamanho,
    largura_maxima_mm
):

    conteudo = str(conteudo)

    largura_texto = stringWidth(
        conteudo,
        fonte,
        tamanho
    )

    largura_maxima = largura_maxima_mm * mm

    if largura_texto <= largura_maxima:
        return tamanho

    if largura_texto == 0:
        return tamanho

    # Reduz apenas textos que excedam
    # o espaço disponível.
    return tamanho * (
        largura_maxima / largura_texto
    )


# =========================================
# LOGOTIPO HISTÓRICO DO RECIBO
# =========================================

def carregar_logo_historica(recibo):
    """
    Recupera o logotipo que foi armazenado
    no banco de dados durante a emissão.
    """

    chaves = recibo.keys()

    # 2.3.0: imagem na tabela "logos"; versões anteriores: na coluna do recibo
    dados_logo = (
        (recibo["logo_imagem"] if "logo_imagem" in chaves else None)
        or (recibo["emissor_logo"] if "emissor_logo" in chaves else None)
    )

    if not dados_logo:
        return None

    return ImageReader(BytesIO(dados_logo))


# =========================================
# 6. GERAÇÃO PRINCIPAL DO RECIBO
# =========================================

def criar_pdf(id_recibo):

    # -------------------------------------
    # CONSULTA AO BANCO DE DADOS
    # -------------------------------------

    recibo = buscar_recibo_por_id(id_recibo)

    if recibo is None:
        log.warning("Recibo %s não encontrado.", id_recibo)
        return None

    
    # =====================================
    # EMPRESA VINCULADA AO RECIBO
    # =====================================

    emissor_razao_social = str(
        recibo["emissor_razao_social"] or ""
    ).strip()

    emissor_cnpj = str(
        recibo["emissor_cnpj"] or ""
    ).strip()

    emissor_cidade = str(
        recibo["emissor_cidade"] or ""
    ).strip()

    if not all((
        emissor_razao_social,
        emissor_cnpj,
        emissor_cidade
    )):
        raise ValueError(
            "Este recibo não possui todos os dados "
            "da empresa emissora cadastrados."
        )


    # -------------------------------------
    # CAMINHO DO PDF
    # -------------------------------------

    PASTA_PDFS.mkdir(
        parents=True,
        exist_ok=True
    )

    numero = f"REC-{id_recibo:06d}"

    caminho = PASTA_PDFS / f"{numero}.pdf"

    # -------------------------------------
    # CONFIGURAÇÃO A4
    # -------------------------------------

    # O PDF é gerado em um arquivo temporário e só substitui
    # o definitivo ao final: nunca fica um PDF pela metade.
    with tempfile.NamedTemporaryFile(
        prefix=f"{numero}_",
        suffix=".tmp",
        dir=PASTA_PDFS,
        delete=False
    ) as arquivo_temporario:
        caminho_temporario = Path(arquivo_temporario.name)

    try:
        _desenhar_recibo(recibo, numero, caminho_temporario)

        try:
            os.replace(caminho_temporario, caminho)

        except PermissionError as erro:
            raise PdfEmUsoError(
                f"O arquivo {caminho.name} está aberto em outro "
                "programa. Feche o PDF e tente novamente."
            ) from erro

    finally:
        caminho_temporario.unlink(missing_ok=True)

    log.info("PDF gerado: %s", caminho.name)

    return caminho


def _desenhar_recibo(recibo, numero, caminho):

    emissor_razao_social = str(recibo["emissor_razao_social"]).strip()
    emissor_cnpj = str(recibo["emissor_cnpj"]).strip()
    emissor_cidade = str(recibo["emissor_cidade"]).strip()

    pdf = canvas.Canvas(
        str(caminho),
        pagesize=A4
    )

    largura, altura = A4

    pdf.setTitle(
        f"Recibo Provisório - {numero}"
    )

    pdf.setAuthor(DESENVOLVEDOR)
    pdf.setCreator(NOME_SOFTWARE)


    # =====================================
    # LOGOTIPO ORIGINAL DO RECIBO
    # =====================================

    logo_historica = carregar_logo_historica(recibo)

    if logo_historica is not None:
        pdf.drawImage(
            logo_historica,
            162 * mm,
            altura - 39 * mm,
            width=30 * mm,
            height=18 * mm,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto"
        )


    # =====================================
    # FUNÇÕES DE DESENHO
    # =====================================

    def y(posicao_mm):

        return altura - posicao_mm * mm

    def linha(x1, x2, posicao_mm):

        pdf.setLineWidth(0.5)

        pdf.line(
            x1 * mm,
            y(posicao_mm),
            x2 * mm,
            y(posicao_mm)
        )

    def texto(
        conteudo,
        x,
        posicao,
        largura_maxima,
        fonte="Helvetica",
        tamanho=11,
        alinhamento="left"
    ):

        conteudo = str(
            conteudo
            if conteudo is not None
            else ""
        )

        tamanho_final = ajustar_fonte(
            conteudo,
            fonte,
            tamanho,
            largura_maxima
        )

        pdf.setFont(
            fonte,
            tamanho_final
        )

        if alinhamento == "center":

            pdf.drawCentredString(
                x * mm,
                y(posicao),
                conteudo
            )

        elif alinhamento == "right":

            pdf.drawRightString(
                x * mm,
                y(posicao),
                conteudo
            )

        else:

            pdf.drawString(
                x * mm,
                y(posicao),
                conteudo
            )

    # =====================================
    # 7. DADOS RECUPERADOS DO SQLITE
    # =====================================

    nome = str(
        recibo["nome"] or ""
    ).strip().upper()

    cpf = str(
        recibo["cpf"] or ""
    ).strip()

    # Código de identificação do aluno
    codigo_aluno = str(
        recibo["codigo_aluno"] or ""
    ).strip()

    # Nome do plano contratado
    plano = str(
        recibo["plano"] or ""
    ).strip()

    valor = formatar_valor(
        recibo["valor_centavos"]
    )

    forma_pagamento = str(
        recibo["forma_pagamento"] or ""
    ).strip()

    formas_exibicao = {
        "PIX CNPJ": "PIXCNPJ",
        "PIX MAQ": "PIXMAQ",
        "Crédito": "C. CRÉDITO",
        "Débito": "C. DÉBITO"
    }

    forma_pagamento = formas_exibicao.get(
        forma_pagamento,
        forma_pagamento
    )

    # Usa o nome completo, quando conhecido
    consultor = formatar_consultor(
        recibo["consultor"]
    )

    data_pagamento = date.fromisoformat(
        str(recibo["data_pagamento"])[:10]
    ).strftime("%d/%m/%Y")

    data_emissao = date.fromisoformat(
        str(recibo["emitido_em"])[:10]
    ).strftime("%d/%m/%Y")

    # Somente letras/números, sem pontuação (igual à 2.1.2
    # para CNPJ numérico; também aceita o CNPJ alfanumérico)
    cnpj_limpo = normalizar_cnpj(emissor_cnpj)

    # =====================================
    # 8. TÍTULO DO RECIBO
    # =====================================

    texto(
        "RECIBO PROVISÓRIO",
        67,
        28,
        110,
        "Helvetica-Bold",
        12,
        "center"
    )

    linha(21, 153, 32)

    # =====================================
    # 9. DECLARAÇÃO INICIAL
    # =====================================

    texto(
        "Declaramos para os devidos fins "
        "de direitos, que recebemos do aluno:",
        21,
        42,
        132,
        "Helvetica-Bold",
        11
    )

    # =====================================
    # 10. NOME COMPLETO E CPF
    # =====================================

    texto(
        f"Sr.(a) {nome}",
        25,
        49,
        89,
        "Helvetica-Bold",
        11
    )

    # 2.4.0: CPF com pontuação (000.000.000-00)
    texto(
        f"CPF: {formatar_cpf(cpf)}",
        118,
        49,
        38,
        "Helvetica-Bold",
        11
    )

    # =====================================
    # 11. MENSAGEM ORIGINAL
    # =====================================

    texto(
        "Cheque(s)*, e autorização(ões) "
        "de débito* para o pagamento do(s) "
        "plano(s) e/ou",
        21,
        56,
        132,
        "Helvetica",
        10.5
    )

    texto(
        "serviço(s) como segue:",
        21,
        63,
        132,
        "Helvetica",
        10.5
    )

    # =====================================
    # 12. CÓDIGO DO ALUNO
    # =====================================

    texto(
        "Código:",
        21,
        72,
        18,
        "Helvetica-Bold",
        11
    )

    texto(
        codigo_aluno,
        40,
        72,
        105,
        "Helvetica-Bold",
        11.5
    )

    # =====================================
    # 13. DESCRIÇÃO DO PAGAMENTO
    # =====================================

    texto(
        "Descrição:",
        21,
        79,
        20,
        "Helvetica-Bold",
        11
    )

    texto(
        DESCRICAO_PADRAO,
        42,
        79,
        108,
        "Helvetica-Bold",
        11
    )

    # =====================================
    # 14. NOME COMPLETO DO ALUNO
    # =====================================

    texto(
        "Aluno:",
        21,
        86,
        18,
        "Helvetica-Bold",
        11
    )

    # Nome em uma única linha; a fonte só é reduzida
    # quando o nome não cabe no espaço disponível.
    texto(
        nome,
        40,
        86,
        115,
        "Helvetica-Bold",
        11.5
    )

    # =====================================
    # 15. TABELA DE PRODUTOS
    # =====================================

    linha(21, 93, 91)

    texto(
        "Produtos",
        21,
        98,
        45,
        "Helvetica",
        11
    )

    texto(
        "Valor",
        83,
        98,
        20,
        "Helvetica",
        11,
        "center"
    )

    # Produto = nome do plano
    texto(
        plano,
        21,
        105,
        45,
        "Helvetica",
        11
    )

    texto(
        valor,
        92,
        105,
        28,
        "Helvetica",
        11,
        "right"
    )

    linha(21, 93, 110)

    # =====================================
    # 16. TOTAL FINAL
    # =====================================

    texto(
        "Total Final",
        21,
        117,
        48,
        "Helvetica-Bold",
        11
    )

    texto(
        valor,
        92,
        117,
        28,
        "Helvetica-Bold",
        11,
        "right"
    )

    linha(21, 93, 122)

    # =====================================
    # 17. DADOS DO RECEBIMENTO
    # =====================================

    texto(
        "Dados do Recebimento",
        21,
        129,
        72,
        "Helvetica-Bold",
        11
    )

    linha(21, 93, 134)

    # =====================================
    # 18. CABEÇALHO DA TABELA
    # =====================================

    texto(
        "Parc",
        29,
        143,
        15,
        tamanho=10.5,
        alinhamento="center"
    )

    texto(
        "Valor",
        51,
        143,
        20,
        tamanho=10.5,
        alinhamento="center"
    )

    texto(
        "Data",
        79,
        143,
        20,
        tamanho=10.5,
        alinhamento="center"
    )

    texto(
        "Aut - Doc/Nsu",
        111,
        143,
        29,
        tamanho=10.5,
        alinhamento="center"
    )

    texto(
        "Forma de PG",
        142,
        143,
        25,
        tamanho=10.5,
        alinhamento="center"
    )

    # =====================================
    # 19. VALORES DO RECEBIMENTO
    # =====================================

    texto(
        "1",
        29,
        151,
        15,
        tamanho=10.5,
        alinhamento="center"
    )

    texto(
        valor,
        51,
        151,
        24,
        tamanho=10.5,
        alinhamento="center"
    )

    texto(
        data_pagamento,
        79,
        151,
        26,
        tamanho=10.5,
        alinhamento="center"
    )

   
    # =====================================
    # AUTENTICAÇÃO DO PAGAMENTO
    # =====================================

    # Recupera o código armazenado no SQLite.
    # Recibos antigos podem não possuir o campo.
    codigo_autenticacao = (
        recibo["codigo_autenticacao"]
        if "codigo_autenticacao" in recibo.keys()
        else None
    )

    # Sem autenticação, mantém o hífen.
    codigo_exibicao = codigo_autenticacao or "-"

    texto(
        codigo_exibicao,
        111,
        151,
        28,
        tamanho=10.5,
        alinhamento="center"
    )


    texto(
        forma_pagamento,
        142,
        151,
        25,
        tamanho=10.5,
        alinhamento="center"
    )

    # =====================================
    # 20. RODAPÉ DA EMPRESA
    # =====================================

    texto(
        emissor_razao_social,
        67,
        164,
        110,
        "Helvetica",
        10.5,
        "center"
    )

    texto(
        f"C.N.P.J / M.F. nr. {formatar_cnpj(cnpj_limpo)}",
        67,
        171,
        120,
        "Helvetica",
        10,
        "center"
    )

    texto(
        f"{emissor_cidade} - {data_emissao}",
        67,
        178,
        110,
        "Helvetica",
        10,
        "center"
    )

    # =====================================
    # 21. CONSULTOR RESPONSÁVEL
    # =====================================

    texto(
        "Consultor:",
        21,
        191,
        18,
        "Helvetica",
        10.5
    )

    texto(
        consultor,
        42,
        191,
        110,
        "Helvetica",
        10.5
    )

    # =====================================
    # 22. NÚMERO DO RECIBO
    # =====================================

    if MOSTRAR_NUMERO_RECIBO:

        texto(
            f"Número do recibo: {numero}",
            21,
            200,
            110,
            "Helvetica",
            9
        )

    # =====================================
    # 23. FINALIZAÇÃO
    # =====================================

    pdf.showPage()
    pdf.save()


# =========================================
# 24. TESTE DIRETO
# =========================================

if __name__ == "__main__":
    criar_pdf(1)
