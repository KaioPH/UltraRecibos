# =========================================
# MODELO DE DADOS LOCAIS DO ULTRA RECIBOS
# =========================================
# Copie este arquivo para "dados_locais.py" e preencha com os dados reais.
# O dados_locais.py fica fora do Git (.gitignore).
# Sem ele, o programa usa os dados de exemplo de configuracoes.py,
# consultores.py e receipt_pdf.py.

# Empresa responsável pela emissão do recibo
RAZAO_SOCIAL = "EMPRESA EXEMPLO LTDA"
CNPJ_EMPRESA = "11.222.333/0001-81"
CIDADE_EMPRESA = "BRASÍLIA"

# Consultores cadastrados na primeira execução
CONSULTORES_INICIAIS = [
    "Consultor Exemplo 1",
    "Consultor Exemplo 2"
]

# Conversão de nomes antigos (curtos) para o nome completo nos PDFs
CONSULTORES_ANTIGOS = {
    "exemplo": "Consultor Exemplo 1"
}
