# Histórico de versões

## 2.5.1 — 14/11/2026

- Histórico: ao abrir, mostra os recibos das últimas 48 horas; a pesquisa
  (nome, CPF ou código) continua procurando nos últimos 90 dias.
- Testes no Windows: a limpeza da pasta temporária não tenta mais apagar o
  arquivo de log aberto (WinError 32).

## 2.5.0 — 14/11/2026

- **Opção J — uma cópia por vez:** ao abrir o programa já aberto, a janela
  existente é trazida para a frente (Windows: mutex do sistema, liberado
  automaticamente ao fechar, mesmo se o programa travar).

## 2.4.0 — 14/11/2026

- **Restauração de backup** (Configurações > Sistema): lista dos backups com
  data, quantidade de recibos e último número; restauração de arquivo externo
  (pendrive); aviso de quantos recibos ficariam de fora; confirmação digitando
  RESTAURAR; o banco atual é guardado em `antes_restauracao_*.db` (permite desfazer);
  opção de restaurar também empresa/logotipo do mesmo dia.
- **Backups:** mantidos os últimos 90 dias. As cópias `antes_*` nunca são apagadas.
- **Recibo (PDF):** CPF com pontuação (000.000.000-00) e CNPJ com pontuação.
  Nome do aluno continua em uma linha (a fonte só diminui quando não cabe;
  espaço disponível na linha "Aluno" ampliado de 108 para 115 mm).
- **Aparência:** nova aba com Automático pelo horário (claro 6h–18h), Seguir o
  Windows, Sempre claro e Sempre escuro. Cores oficiais da Ultra mantidas.
- Correção: colunas do cartão Pagamento com largura fixa (texto do menu não é cortado).

## 2.3.0 — 13/11/2026

Aprovado por Kaio: propostas D, E, G e H. Layout do PDF inalterado
(comparado pixel a pixel, inclusive recibos com logotipo migrados).

- **D — Logotipo sem repetição:** nova tabela `logos`; cada recibo guarda só a
  referência (`emissor_logo_hash`). Na primeira abertura, os recibos existentes
  são migrados automaticamente, com cópia completa do banco antes
  (`backups\antes_migracao_logos_AAAAMMDD_HHMMSS.db`) e conferência byte a byte.
- **E — Índice** `idx_recibos_emitido_em` para o histórico de 90 dias.
- **G — Planos e formas de pagamento editáveis** (Configurações > Planos e
  pagamentos): adicionar, renomear, desativar/reativar, ordenar e marcar
  "exige código de autenticação". Recibos antigos mantêm o nome gravado.
- **H — Alerta de possível duplicidade** (mesmo CPF + valor + data de pagamento
  nos últimos 90 dias). Apenas avisa; o botão passa a "Salvar mesmo assim".
- Atenção: após abrir a 2.3.0, a versão 2.2.0 ou anterior mostraria os recibos
  migrados sem logotipo. Para voltar de versão, use o arquivo
  `antes_migracao_logos_*.db`.

## 2.2.0 — 13/11/2026

Sem alteração de estrutura do banco, de regras de negócio, de cálculos
ou do layout do PDF (PDF verificado como idêntico pixel a pixel).

### Correções
- Rótulo do código de autenticação indicava "6-8 caracteres"; a regra é 2 a 10.
- `empresa.json` danificado impedia emitir recibos e fechava as Configurações
  sem permitir correção.
- Logotipo personalizado danificado impedia o programa de abrir.
- Logotipo novo só aparecia no cabeçalho após reiniciar o programa.
- Reimpressão falhava com o PDF aberto no leitor; PDF podia ficar incompleto
  em caso de erro (agora a gravação é atômica).
- Erro de banco na abertura exibia traceback técnico.
- Pesquisa tratava `%` e `_` como curingas; CPF parcial com pontuação não era encontrado.
- Cadastro duplicado de consultor mostrava erro técnico do SQLite.
- Conexões SQLite agora são sempre fechadas.
- Versão interna desatualizada (2.0.0).
- CNPJ alfanumérico (Receita Federal, 2026) era gravado/impresso sem as letras;
  CNPJ agora tem os dígitos verificadores conferidos.

### Melhorias
- Nova interface: dois cartões (Aluno / Pagamento), rótulos acima dos campos,
  campo inválido destacado em vermelho, máscara de CPF, valor padronizado
  (9,9 → 9,90), Enter avança, Ctrl+S salva, botão Limpar, barra de status
  com último backup e versão. Cabe em telas 1366x768 com zoom de 125%.
- Confirmação do lançamento mostra todos os dados (incluindo autenticação).
- Histórico abre com os recibos recentes, pesquisa enquanto digita e mostra
  CPF, código, consultor, forma de pagamento, autenticação e data de emissão.
- Configurações: nova aba Sistema (versão, pastas, estatísticas, backup manual),
  consultores com adição direta, ativos/inativos destacados, remover logotipo.
- Backup inclui `empresa.json` e logotipo.
- Logotipo reduzido para no máximo 1200 px ao salvar (banco menor).
- Log de funcionamento em `logs\ultrarecibos.log` (rotativo, sem dados pessoais).
- Backup e limpeza executados depois que a janela aparece (abertura mais rápida).
- Testes automatizados (37) em pasta isolada.
- Build reproduzível (`build_windows.bat`), UPX desativado, instalador remove
  bibliotecas antigas ao atualizar.
