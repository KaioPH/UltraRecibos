
# =========================================
# CONFIGURAÇÕES DO ULTRA RECIBOS
# =========================================

# Identificação do software
NOME_SOFTWARE = "Ultra Recibos"
VERSAO_SOFTWARE = "2.5.1"
DESENVOLVEDOR = "Kaio Phyllipe Rodrigues"

# Empresa responsável pela emissão do recibo
# (valores padrão usados enquanto nenhuma empresa
# for cadastrada em Configurações)
# Os dados reais ficam em dados_locais.py (fora do Git).
# Sem esse arquivo, o programa usa os dados de exemplo abaixo.
RAZAO_SOCIAL = "EMPRESA EXEMPLO LTDA"
CNPJ_EMPRESA = "11.222.333/0001-81"
CIDADE_EMPRESA = "BRASÍLIA"

try:
    from dados_locais import RAZAO_SOCIAL, CNPJ_EMPRESA, CIDADE_EMPRESA
except ImportError:
    pass

# Informações do recibo
DESCRICAO_PADRAO = "PAGAMENTO AVULSO - MANUAL"
MOSTRAR_NUMERO_RECIBO = False

# Retenção dos PDFs e período da pesquisa no histórico (dias)
DIAS_RETENCAO = 90

# Recibos exibidos ao abrir o histórico, sem pesquisar (horas)
HORAS_HISTORICO_INICIAL = 48


# =========================================
# OPÇÕES DO FORMULÁRIO
# =========================================

TEXTO_SELECIONE_PLANO = "Selecione um plano"
TEXTO_SELECIONE_PAGAMENTO = "Selecione a forma de pagamento"
TEXTO_SELECIONE_CONSULTOR = "Selecione o consultor"

PLANOS = [
    "Diária",
    "Gold",
    "Gold Pass",
    "Gold Pro",
    "Ultra 360",
    "Ultra Pilates",
    "Lojista",
    "Negociação de Débito",
    "Personal",
    "Plano Anual",
    "Tx manutenção"
]

FORMAS_PAGAMENTO = [
    "PIX CNPJ",
    "PIX MAQ",
    "Crédito",
    "Débito",
    "Dinheiro",
    "DIN + MAQ",
    "DIN + CNPJ"
]

# Modalidades que exigem código de autenticação
PAGAMENTOS_COM_AUTENTICACAO = {
    "Crédito",
    "Débito",
    "DIN + MAQ"
}

# Código de autenticação: letras e números
AUTENTICACAO_MIN = 2
AUTENTICACAO_MAX = 10
