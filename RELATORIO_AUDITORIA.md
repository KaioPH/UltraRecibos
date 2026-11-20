# Relatório de auditoria técnica — Ultra Recibos 2.1.2 → 2.2.0

Data: 13/11/2026 · Base analisada: `UltraRecibos_Fonte_2_1_2_20261113_230705.zip`
O ZIP original não foi alterado. Todo o trabalho foi feito em uma cópia.

---

## 1. Problemas encontrados

Gravidade: **A** alta · **M** média · **B** baixa. Situação: ✅ corrigido · 🟡 mitigado · ⏸ aguarda aprovação.

| # | Grav. | Problema (confirmado no código) | Situação |
|---|---|---|---|
| 1 | A | **Configurações sem autenticação.** `tela_admin.py` é "SEM LOGIN". Os módulos `seguranca_admin.py` e `recuperacao_admin.py` (PBKDF2, 600.000 iterações, códigos de recuperação) existem, mas não são chamados. Qualquer funcionário pode alterar razão social/CNPJ impressos nos recibos e desativar consultores. | ⏸ Proposta A |
| 2 | A | Rótulo do campo dizia **"Código de autenticação (6-8 caracteres)"**, enquanto a validação aceita 2 a 10 (comentário no código: "até 8"). | ✅ |
| 3 | A | `empresa.json` danificado: `carregar_empresa()` lançava erro → salvar recibo falhava **e** a tela de Configurações fechava sozinha. Não havia como corrigir pela interface. | ✅ |
| 4 | M | Logotipo personalizado danificado → exceção no carregamento do módulo → **programa não abria**. | ✅ |
| 5 | M | `atualizar_logo_cabecalho()` existia, mas **nunca era chamada**: logo novo só aparecia após reiniciar. | ✅ |
| 6 | M | Cada recibo grava uma cópia do logotipo (BLOB). Imagens de até 4000×4000 eram aceitas sem redução (PNG RGBA pode ter vários MB). O banco cresce rapidamente e o backup completo feito após **cada** recibo fica progressivamente mais lento. | 🟡 logo limitado a 1200 px · ⏸ Proposta D |
| 7 | M | Backups diários nunca são removidos (acúmulo indefinido) e ficam no mesmo disco do banco. | ⏸ Proposta C |
| 8 | M | **Não existe restauração** de backup no programa (apenas criação). | ⏸ Proposta B |
| 9 | M | `empresa.json` e o logotipo não eram incluídos no backup. | ✅ |
| 10 | M | Janela 980×620 (mínimo 850×590). Em notebook 1366×768 com zoom de 125% (padrão do Windows), a altura real passa de 768 px e os botões ficam cortados. | ✅ |
| 11 | M | ReportLab gravava direto no PDF final: com o PDF aberto no leitor, a reimpressão falhava (arquivo bloqueado pelo Windows); em caso de erro, podia ficar um PDF incompleto. | ✅ |
| 12 | M | `inicializar_consultores()` rodava antes do tratamento de erro do banco (erro virava traceback técnico). Backup e limpeza rodavam antes da janela aparecer. | ✅ |
| 13 | M | Falha ao gerar o PDF após salvar mantinha o formulário preenchido (risco de lançamento em duplicidade, apesar do aviso). | ✅ formulário limpo |
| 14 | B | `print()` não aparece no .exe (sem console): erros não ficavam registrados em lugar nenhum. | ✅ log rotativo |
| 15 | B | Pesquisa: `%` e `_` funcionavam como curingas; CPF parcial com pontuação não era encontrado. | ✅ |
| 16 | B | Consultor duplicado exibia "UNIQUE constraint failed: consultores.nome". | ✅ |
| 17 | B | `with sqlite3.connect(...)` faz commit, mas não fecha a conexão. | ✅ `conectar()` |
| 18 | B | `VERSAO_SOFTWARE = "2.0.0"` enquanto exe/instalador = 2.1.2. | ✅ 2.2.0 em todos |
| 19 | B | Instalador apontava para `dist_validacao_2_1_2` (inexistente no pacote); sem script de build; UPX ativo (associado a falsos positivos de antivírus); atualização não removia bibliotecas antigas de `_internal`. | ✅ |
| 20 | B | **CNPJ alfanumérico** (emitido pela Receita desde 31/07/2026): `salvar_empresa` removia as letras e o PDF imprimia só os dígitos. Dígitos verificadores não eram conferidos. | ✅ |
| 21 | B | Conferência não exibia o código de autenticação; a confirmação "Deseja salvar?" não mostrava os dados. | ✅ |
| 22 | Org. | 30 cópias manuais (`*_backup*.py`, `.bak`, `.iss`, `.spec`) e ~150 MB de pastas `build_*`, `dist_*`, `teste_instalacao` misturadas ao código. Scripts `teste_*.py` gravam no banco de desenvolvimento (ex.: `teste_insercao.py` insere recibo). | ✅ movidos para `_historico_versoes/` (nada apagado) |

### Regras do sistema — conferência no código

| Regra | Existe? | Evidência / observação |
|---|---|---|
| Autenticação alfanumérica 2–10 | Sim | Regex `[A-Za-z0-9]{2,10}`, exigida só em Crédito, Débito e DIN + MAQ. Filtro remove símbolos e limita a 10. Testado. |
| Zeros à esquerda | Sim | `codigo_aluno`, `codigo_autenticacao` e `cpf` são TEXT. Testado com "000123" e "00A12" (banco e PDF). |
| Identificação aluno/consultor | Sim | Nome, CPF (dígitos verificadores), código; consultor da lista de ativos, gravado como texto (renomear não altera recibos antigos). |
| Recibo provisório em PDF | Sim | `receipt_pdf.py`, título "RECIBO PROVISÓRIO". |
| Histórico e reimpressão | Sim | Pesquisa limitada a 90 dias por `emitido_em`, 50 resultados. Reimpressão regera o PDF a partir do banco, sem novo registro. Testado. |
| Dados históricos da empresa | Sim | Colunas `emissor_razao_social/cnpj/cidade` e `emissor_logo` gravadas na emissão. Testado com troca de empresa e logo. |
| Backup consistente do SQLite | Sim | API `backup()` + `PRAGMA integrity_check` + substituição atômica. Testado. |
| Retenção de 90 dias | Parcial | Aplica-se aos **PDFs** (apagados ao abrir o programa) e ao **período do histórico**. Os registros no banco (incluindo CPF) são mantidos para sempre — ver Proposta I. |
| Limpeza sem afetar registros | Sim | Só `REC-<número>.pdf`, ignora links, órfãos e datas inválidas; nunca apaga registros. Testado. |

---

## 2. Melhorias realizadas (código)

- **`database.py`**: `conectar()` (commit/rollback e fechamento garantido, timeout 10 s); migração de colunas unificada; recibo, empresa e logo gravados em uma única instrução; `listar_recibos_recentes()`, `estatisticas_banco()`; pesquisa com escape de curingas e sem carregar o BLOB do logo na lista.
- **`receipt_pdf.py`**: gravação em arquivo temporário + `os.replace`; erro específico `PdfEmUsoError`; CNPJ alfanumérico. **Layout intocado.**
- **`backup.py`**: inclui `empresa.json` e logo (`configuracao_AAAAMMDD/`); `listar_backups()`, `ultimo_backup()`; log.
- **`limpeza_pdfs.py`**: uma conexão para todos os arquivos (antes: uma por PDF); retorna resumo; mesmas regras.
- **`empresa_config.py`**: CNPJ numérico/alfanumérico com dígitos verificadores; mensagem clara para JSON danificado; logo reduzido a 1200 px; `remover_logo_empresa()`.
- **`consultores.py`**: mensagens amigáveis para duplicidade.
- **`validacoes.py`** (novo): regras extraídas de `main.py` sem alteração + máscaras, CNPJ, escape de pesquisa.
- **`registro.py`** (novo): log em `logs\ultrarecibos.log` (5 × 1 MB), sem CPF/nome/valores.
- **`caminhos.py`**: `ULTRARECIBOS_DADOS` para testes isolados; `caminho_asset()` centralizado.
- **`configuracoes.py`**: versão 2.2.0; planos, formas de pagamento e limites centralizados (mesmos valores).
- **Inicialização**: banco preparado antes da interface, com mensagem amigável; backup/limpeza 0,4 s após a janela aparecer; erros inesperados de botões vão para o log e são exibidos.

---

## 3. Melhorias visuais (implementadas)

| Elemento | Antes | Problema | Agora | Benefício |
|---|---|---|---|---|
| Formulário | 8 linhas empilhadas, rótulo à esquerda | Alto demais; corta em 1366×768 @125% | Dois cartões: **Dados do aluno** / **Pagamento**, rótulos acima | Agrupamento lógico, cabe em telas pequenas |
| Menus | Fundo turquesa sólido em todos | Competiam com os botões de ação | Fundo neutro, seta turquesa | Ação principal (laranja) se destaca |
| Autenticação | Surge abaixo do pagamento e empurra o layout | Layout "pula"; rótulo errado (6-8) | Ao lado da forma de pagamento; rótulo 2–10 | Sem saltos, regra correta |
| Erros | Só caixa de mensagem genérica ("Preencha todos os campos") | Funcionário não sabe qual campo | Campo destacado em vermelho + foco + nome do campo | Correção imediata |
| Foco | Sem indicação | Difícil saber onde digita | Borda turquesa no campo ativo | Orientação visual |
| CPF / Valor | Digitação livre | Erros de formatação | Máscara 000.000.000-00; valor padronizado (9,9 → 9,90) | Menos erros |
| Teclado | Somente mouse | Lento no balcão | Enter avança, Ctrl+S salva, Ctrl+H histórico, F5 confere | Agilidade |
| Confirmação | "Deseja salvar este recibo e gerar o PDF?" | Não mostrava os dados | Resumo completo + "Salvar e gerar PDF" / "Voltar e corrigir" | Conferência real antes de gravar |
| Botões | 3 botões grandes; Histórico ao lado de Conferir | Hierarquia confusa | Limpar · Conferir · **SALVAR** (laranja, largo); Histórico e Configurações no topo | Ação principal clara |
| Rodapé | — | Sem retorno após salvar | Barra de status: último recibo, último backup, versão | Feedback contínuo |
| Histórico | Vazio até pesquisar; botão "Pesquisar" obrigatório | Passo extra | Abre com os recentes; pesquisa ao digitar; contador; mais dados por linha | Reimpressão em 1 clique |
| Configurações | Campos centralizados, 780×720 | Não cabia em 768 px; sem informações do sistema | Abas Empresa / Consultores / **Sistema**, rolagem, status Ativo/Inativo, backup manual | Administração completa |
| Janelas | Podiam abrir atrás da principal; várias cópias do histórico | Confusão | Centralizadas, trazidas à frente, instância única | Previsibilidade |

Capturas (dados fictícios) em `docs/capturas/`: `antes_principal.png` e `depois_*.png`.

---

## 4. Arquivos modificados

**Reescritos (mesmas funcionalidades):** `main.py`, `tela_admin.py`.
**Alterados:** `database.py`, `receipt_pdf.py`, `backup.py`, `limpeza_pdfs.py`, `empresa_config.py`, `consultores.py`, `seguranca_admin.py`, `recuperacao_admin.py` (somente conexão), `caminhos.py`, `configuracoes.py`, `UltraRecibos.spec`, `UltraRecibos_Instalador.iss`, `versao_windows.txt`.
**Novos:** `tema.py`, `dialogos.py`, `tela_historico.py`, `validacoes.py`, `registro.py`, `tests/` (4 arquivos de teste + utilitários), `build_windows.bat`, `requirements.txt`, `README.md`, `CHANGELOG.md`, este relatório, `docs/capturas/`.
**Movidos (preservados):** 30 cópias manuais e 4 scripts `teste_*.py` → `_historico_versoes/`.
**Não incluídos no ZIP:** `build_*`, `dist_*`, `teste_instalacao` (artefatos gerados, ~148 MB; continuam no ZIP original).

## 5. Justificativa técnica

- Fechar conexões e gravar arquivos de forma atômica evita bloqueios típicos do Windows e arquivos corrompidos.
- Separar validações (`validacoes.py`) permite testá-las automaticamente; as regras foram copiadas sem alteração.
- Logotipo limitado a 1200 px: impresso em 30 × 18 mm, equivale a ~1000 dpi — sem perda visível, com banco e backups bem menores.
- Log em arquivo é a única forma de diagnosticar falhas em um .exe sem console.
- UPX é desaconselhado pela própria documentação do PyInstaller quando há DLLs do sistema; aumenta falsos positivos.
- `[InstallDelete]` em `_internal` evita mistura de bibliotecas quando a versão do Python muda entre builds.
- Limpar o formulário quando o PDF falha impede o segundo lançamento do mesmo pagamento; o recibo continua disponível no Histórico.

---

## 6. Testes realizados

Ambiente: Linux, Python 3.12, customtkinter 6.0.0, ReportLab 5.1.0, Pillow 13, PyInstaller 6.22, tela virtual Xvfb. Somente dados fictícios, em pasta temporária.

| Teste | Resultado |
|---|---|
| `py_compile` em todos os módulos | Aprovado |
| `pyflakes` (imports/variáveis não usados, nomes indefinidos) | Aprovado, sem avisos |
| Suíte automatizada `tests/executar_testes.py` — 37 testes (validações, banco, PDF, backup, limpeza, migração, consultores, interface) | **37 aprovados** |
| Banco gerado pela versão 2.1.2 original aberto pela 2.2.0, PDFs regenerados | Aprovado |
| Migração de banco no esquema 1.x (sem colunas novas), execução repetida | Aprovado, sem perda |
| PDF 2.2.0 × PDF 2.1.2 (mesmo banco) — comparação pixel a pixel | **Idênticos** (2 recibos) |
| Conteúdo do PDF (nome, CPF, código "000123", autenticação "00A12", valor, forma, consultor) | Aprovado |
| Retenção: PDFs de 10, 89 e 95 dias + órfão + arquivo fora do padrão | Só o de 95 dias apagado; registro mantido e PDF regerável |
| Backup: integridade, conteúdo, cópia da configuração, sem temporários | Aprovado |
| Interface: fluxo completo de salvamento, validações apontando o campo, filtro da autenticação, máscaras, histórico, reimpressão, configurações | Aprovado |
| Layout em 1366×768 com escala 125% | Cabe na tela (captura em `docs/capturas`) |
| Build PyInstaller (Linux) + execução do executável gerado | Aprovado após incluir `PIL._tkinter_finder` (necessário só fora do Windows) |

**Não executados (sem ambiente Windows disponível):** execução no Windows 10/11, build PyInstaller no Windows, compilação do Inno Setup, Python 3.14 (versão do seu build original), abertura do PDF pelo `os.startfile`, impressão física. Execute `build_windows.bat` (roda os testes antes do build) e faça um teste manual com dados fictícios antes de instalar na recepção.

---

## 7. Pontos que ainda precisam de atenção — propostas que dependem da sua aprovação

Estas mudanças alteram comportamento essencial, regras de negócio, o PDF ou o banco; **não foram implementadas**.

| ID | Proposta | Impacto |
|---|---|---|
| **A** | Reativar o login das Configurações (código pronto: usuário/senha PBKDF2 + 6 códigos de recuperação). Primeiro acesso cria o administrador. | Segurança — **recomendação prioritária** |
| **B** | Restauração de backup na aba Sistema (protegida pelo login): valida integridade, guarda cópia do banco atual antes de substituir, reinicia o programa. | Recuperação de desastres |
| **C** | Retenção de backups: manter os últimos 30 diários + 1 por mês por 12 meses. | Disco |
| **D** | Deduplicar logotipos: tabela `logos(hash, imagem)` e coluna `emissor_logo_hash` (migração automática dos recibos existentes). | Banco e backups muito menores; alteração de estrutura |
| **E** | Índices em `recibos(emitido_em)`, `(cpf)`, `(codigo_aluno)`. | Histórico rápido com milhares de recibos |
| **F** | PDF: CPF/CNPJ formatados, número do recibo visível (`MOSTRAR_NUMERO_RECIBO`), quebra de linha em nomes longos (hoje a fonte é reduzida), fonte TrueType embutida para caracteres fora do Latin-1. | Altera o documento |
| **G** | Planos e formas de pagamento editáveis em Configurações (hoje fixos no código). | Regra de negócio |
| **H** | Alerta de possível duplicidade (mesmo CPF + valor + data em poucos minutos). | Regra de negócio |
| **I** | LGPD: os registros com CPF ficam no banco indefinidamente. Definir prazo de retenção/anonimização dos dados pessoais. | Conformidade |
| **J** | Impedir duas instâncias abertas ao mesmo tempo (mutex do Windows). | Estabilidade |
| **K** | Assinatura digital do executável (evita alerta do SmartScreen). | Instalação; requer certificado |

Observações adicionais:
- Backups ficam no mesmo disco: recomenda-se cópia periódica para pendrive/nuvem (aviso incluído na aba Sistema).
- `CONSULTORES_ANTIGOS` em `receipt_pdf.py` mantém nomes fixos para recibos antigos; necessário enquanto houver recibos com apelidos.
- A recuperação de acesso invalida os 6 códigos de uma vez (`recuperacao_admin.py`) — comportamento a confirmar se a Proposta A for aprovada.

## 8. Recomendações para futuras versões

1. Aprovar A + B (segurança e restauração) como prioridade.
2. Avaliar D + E quando o banco passar de algumas centenas de MB (o tamanho aparece em Configurações > Sistema).
3. Integrar `build_windows.bat` a um repositório Git (GitHub) para histórico de versões, em vez de cópias `_backup` manuais.
4. Publicar notas de versão a cada build (CHANGELOG.md).
5. Considerar exportação do histórico em planilha para conferência de caixa.

### Avaliação de versão

Adotada **2.2.0**: mudanças compatíveis, sem alteração de banco, regras ou PDF.
Uma **3.0.0** se justifica se as propostas A, B, D e G forem aprovadas: novo fluxo administrativo obrigatório, migração de estrutura do banco e dados de negócio configuráveis — mudanças que alteram a forma de uso e não permitem voltar à 2.x sem cuidado.

---

## Atualização 2.3.0 (propostas aprovadas)

| Proposta | Situação |
|---|---|
| D — logotipo sem repetição | ✅ Implementada, com migração automática + cópia prévia do banco |
| E — índice do histórico | ✅ Implementada (`emitido_em`). Índices em CPF/código não foram criados: a pesquisa usa "contém" (`LIKE '%texto%'`), que o SQLite não acelera com índice. |
| G — planos e pagamentos editáveis | ✅ Implementada (nova aba) |
| H — alerta de duplicidade | ✅ Implementada, sem bloquear o lançamento |
| B, C, F, J, K | Aguardando decisão |
| I — LGPD | Mantido como está (registros preservados) |

Testes: 44 automatizados aprovados (7 novos), PDFs idênticos à 2.1.2 antes e depois da
migração de logotipos, build PyInstaller (Linux) e execução do executável aprovados.
Não testado no Windows.

---

## Atualização 2.4.0

| Item | Situação |
|---|---|
| B — Restauração de backup | ✅ Implementada (sem senha; proteção por confirmação digitada e cópia prévia do banco) |
| C — Retenção de backups | ✅ Últimos 90 dias diários |
| Pesquisa > 90 dias | Não implementada (mantido o histórico de 90 dias, conforme decisão) |
| F1 — CPF com pontuação no PDF | ✅ |
| F2 — CNPJ com pontuação no PDF | ✅ |
| F3 — Número do recibo | Não implementado (decisão) |
| F4 — Nome longo | Mantido em uma linha com redução automática da fonte; largura útil ampliada |
| K — Assinatura digital | Descartada (uso local) |
| Aparência claro/escuro/automático | ✅ |
| J — Instância única | ✅ Implementada na 2.5.0 |

Testes: 50 automatizados aprovados. Um defeito encontrado pelos testes foi corrigido antes
da entrega (duas restaurações no mesmo segundo podiam sobrescrever a cópia de segurança).
Defeito visual corrigido: na troca para o tema escuro, textos sobre áreas com rolagem ficavam
com fundo branco. Não testado no Windows.
