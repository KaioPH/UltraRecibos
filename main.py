
"""
Ultra Recibos - emissão de recibos provisórios em PDF.

Janela principal: formulário do recibo, conferência,
salvamento, geração do PDF e acesso ao histórico.
"""


from datetime import date, datetime
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

import tema as t

from caminhos import caminho_asset
from configuracoes import (
    NOME_SOFTWARE,
    VERSAO_SOFTWARE,
    DIAS_RETENCAO,
    AUTENTICACAO_MIN,
    AUTENTICACAO_MAX,
    TEXTO_SELECIONE_PLANO,
    TEXTO_SELECIONE_PAGAMENTO,
    TEXTO_SELECIONE_CONSULTOR
)
from registro import obter_logger
from validacoes import (
    validar_cpf,
    validar_valor,
    validar_data,
    valor_para_centavos,
    formatar_reais,
    formatar_cpf,
    mascarar_cpf,
    mascarar_data,
    normalizar_valor_digitado,
    filtrar_autenticacao,
    validar_autenticacao,
    somente_digitos
)


log = obter_logger("main")


# =========================================
# APLICATIVO
# =========================================

class AplicativoRecibos:

    def __init__(self):

        t.aplicar_tema()

        self.janela = ctk.CTk()
        self.janela.title(f"{NOME_SOFTWARE} {VERSAO_SOFTWARE}")
        self.janela.configure(fg_color=t.COR_FUNDO)
        self.janela.minsize(900, 500)
        t.aplicar_icone(self.janela)
        t.centralizar(self.janela, 1040, 550)

        # Erros inesperados em botões/eventos: registra no log
        # e informa o usuário, em vez de falhar em silêncio.
        self.janela.report_callback_exception = self._erro_inesperado

        self.salvamento_em_andamento = False
        self.tela_configuracoes = None
        self.tela_historico = None
        self.logo_imagem = None

        self._preparar_banco()

        self._montar_cabecalho()
        self._montar_formulario()
        self._montar_acoes()
        self._montar_rodape()
        self._atalhos()

        self.campo_nome.focus_set()

        # Tarefas de manutenção depois que a janela aparece
        # (deixa a abertura do programa mais rápida).
        self.janela.after(400, self._manutencao_inicial)

        # Aparência automática pelo horário (verifica a cada minuto)
        self.janela.after(60_000, self._verificar_aparencia)

    # =====================================
    # INICIALIZAÇÃO
    # =====================================

    def _preparar_banco(self):

        try:
            from database import criar_banco
            from consultores import inicializar_consultores
            from opcoes import inicializar_opcoes

            criar_banco()
            inicializar_consultores()
            inicializar_opcoes()

        except Exception as erro:

            log.exception("Falha ao preparar o banco de dados")

            messagebox.showerror(
                "Erro no banco de dados",
                "Não foi possível preparar o banco de dados:\n"
                f"{erro}\n\nO programa será encerrado."
            )

            self.janela.destroy()
            raise SystemExit(1)

    def _manutencao_inicial(self):

        from backup import criar_backup
        from limpeza_pdfs import limpar_pdfs_antigos

        # Backup automático do banco de dados
        try:
            if criar_backup() is None:
                messagebox.showwarning(
                    "Aviso de backup",
                    "Não foi possível criar a cópia de segurança "
                    "do banco de dados.\n\nOs recibos continuam "
                    "sendo salvos normalmente. Se o aviso se "
                    "repetir, avise o responsável pelo sistema.",
                    parent=self.janela
                )

        except Exception as erro:
            log.exception("Falha no backup inicial")
            messagebox.showwarning(
                "Erro no backup",
                f"Falha ao criar o backup:\n{erro}",
                parent=self.janela
            )

        # Limpeza automática de PDFs antigos
        try:
            limpar_pdfs_antigos(simular=False)
        except Exception:
            log.exception("Erro durante a limpeza dos PDFs")

        self._atualizar_status_backup()

    def _verificar_aparencia(self):

        try:
            t.aplicar_tema()
        except Exception:
            log.exception("Falha ao aplicar a aparência")

        self.janela.after(60_000, self._verificar_aparencia)

    def recarregar_dados(self):
        """
        Atualiza o formulário após alterações nas Configurações
        (inclusive depois de restaurar um backup).
        """

        self.atualizar_consultores_formulario()
        self.atualizar_opcoes_formulario()
        self.atualizar_logo_cabecalho()
        self._atualizar_status_backup()

    def _erro_inesperado(self, tipo, valor, rastreio):

        log.error("Erro inesperado", exc_info=(tipo, valor, rastreio))

        messagebox.showerror(
            "Erro inesperado",
            "Ocorreu um erro inesperado:\n"
            f"{valor}\n\nOs detalhes foram registrados no "
            "arquivo de log (Configurações > Sistema).",
            parent=self.janela
        )

    # =====================================
    # CABEÇALHO
    # =====================================

    def _montar_cabecalho(self):

        cabecalho = ctk.CTkFrame(self.janela, fg_color="transparent")
        cabecalho.pack(fill="x", padx=22, pady=(14, 8))

        self.logo_label = ctk.CTkLabel(cabecalho, text="")
        self.logo_label.pack(side="left", padx=(0, 14))
        self.atualizar_logo_cabecalho()

        titulos = ctk.CTkFrame(cabecalho, fg_color="transparent")
        titulos.pack(side="left")

        ctk.CTkLabel(
            titulos,
            text="ULTRA RECIBOS",
            font=t.FONTE_TITULO,
            text_color=t.COR_PRINCIPAL
        ).pack(anchor="w")

        ctk.CTkLabel(
            titulos,
            text="Emissão e gerenciamento de recibos provisórios",
            font=t.FONTE_SUBTITULO,
            text_color=t.COR_SECUNDARIO
        ).pack(anchor="w")

        t.botao(
            cabecalho,
            "⚙  Configurações",
            self.abrir_configuracoes,
            estilo="neutro",
            width=150
        ).pack(side="right")

        t.botao(
            cabecalho,
            "Histórico / Reimprimir",
            self.abrir_historico,
            estilo="roxo",
            width=200
        ).pack(side="right", padx=(0, 10))

    def _carregar_logo(self):

        from empresa_config import obter_logo_empresa

        candidatos = []

        logo_personalizada = obter_logo_empresa()

        if logo_personalizada is not None:
            candidatos.append(logo_personalizada)

        # Logo original como alternativa
        candidatos.append(caminho_asset("logo_ultra_verde.png"))

        for caminho in candidatos:

            try:
                with Image.open(caminho) as arquivo:
                    imagem = arquivo.convert("RGBA")

                # Remove margens transparentes
                limites = imagem.getchannel("A").getbbox()

                if limites:
                    imagem = imagem.crop(limites)

                # Preserva a proporção da imagem
                imagem.thumbnail((120, 52), Image.Resampling.LANCZOS)

                return ctk.CTkImage(
                    light_image=imagem,
                    dark_image=imagem,
                    size=imagem.size
                )

            except (OSError, ValueError) as erro:
                log.warning("Logotipo não carregado (%s): %s", caminho, erro)

        return None

    def atualizar_logo_cabecalho(self):

        self.logo_imagem = self._carregar_logo()

        if self.logo_imagem is not None:
            self.logo_label.configure(image=self.logo_imagem, text="")
        else:
            self.logo_label.configure(image=None, text="")

    # =====================================
    # FORMULÁRIO
    # =====================================

    def _campo(self, pai, linha, coluna, texto, widget, colspan=1):
        """
        Posiciona rótulo (acima) e campo (abaixo) na grade.
        """

        rotulo = t.rotulo(pai, texto, obrigatorio=True)
        rotulo.grid(
            row=linha * 2,
            column=coluna,
            columnspan=colspan,
            sticky="w",
            padx=6,
            pady=(6, 2)
        )

        widget.grid(
            row=linha * 2 + 1,
            column=coluna,
            columnspan=colspan,
            sticky="ew",
            padx=6,
            pady=(0, 6)
        )

        return rotulo

    def _montar_formulario(self):

        corpo = ctk.CTkFrame(self.janela, fg_color="transparent")
        corpo.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        corpo.grid_columnconfigure(0, weight=1, uniform="cartoes")
        corpo.grid_columnconfigure(1, weight=1, uniform="cartoes")
        corpo.grid_rowconfigure(0, weight=1)

        # ---------------------------------
        # CARTÃO: DADOS DO ALUNO
        # ---------------------------------

        cartao_aluno, aluno = t.cartao(corpo, "Dados do aluno", t.COR_PRINCIPAL)
        cartao_aluno.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)

        aluno.grid_columnconfigure(0, weight=1, uniform="aluno")
        aluno.grid_columnconfigure(1, weight=1, uniform="aluno")

        self.campo_nome = t.entrada(aluno, "Nome completo do aluno")
        self._campo(aluno, 0, 0, "Nome completo", self.campo_nome, colspan=2)

        self.campo_cpf = t.entrada(aluno, "000.000.000-00")
        self._campo(aluno, 1, 0, "CPF", self.campo_cpf)

        self.campo_codigo = t.entrada(aluno, "Código do aluno")
        self._campo(aluno, 1, 1, "Código do aluno", self.campo_codigo)

        self.menu_consultor = t.menu_opcoes(aluno, [TEXTO_SELECIONE_CONSULTOR])
        self._campo(
            aluno, 2, 0, "Consultor responsável", self.menu_consultor, colspan=2
        )
        self.atualizar_consultores_formulario()

        # ---------------------------------
        # CARTÃO: PAGAMENTO
        # ---------------------------------

        cartao_pg, pagamento = t.cartao(corpo, "Pagamento", t.COR_LARANJA)
        cartao_pg.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        pagamento.grid_columnconfigure(0, weight=1, uniform="pagamento")
        pagamento.grid_columnconfigure(1, weight=1, uniform="pagamento")

        self.menu_plano = t.menu_opcoes(
            pagamento,
            [TEXTO_SELECIONE_PLANO],
            command=lambda _v: self._limpar_erro(self.menu_plano)
        )
        self._campo(pagamento, 0, 0, "Plano", self.menu_plano)

        self.campo_valor = t.entrada(pagamento, "Ex.: 9,90")
        self._campo(pagamento, 0, 1, "Valor pago (R$)", self.campo_valor)

        self.menu_pagamento = t.menu_opcoes(
            pagamento,
            [TEXTO_SELECIONE_PAGAMENTO],
            command=self._ao_mudar_pagamento
        )
        self._campo(pagamento, 1, 0, "Forma de pagamento", self.menu_pagamento)

        # Código de autenticação (somente cartão / maquininha)
        self.variavel_autenticacao = ctk.StringVar()
        self.variavel_autenticacao.trace_add("write", self._filtrar_autenticacao)

        self.campo_autenticacao = t.entrada(
            pagamento,
            f"{AUTENTICACAO_MIN} a {AUTENTICACAO_MAX} letras ou números",
            textvariable=self.variavel_autenticacao
        )
        self.rotulo_autenticacao = self._campo(
            pagamento,
            1,
            1,
            f"Autenticação ({AUTENTICACAO_MIN} a {AUTENTICACAO_MAX} caracteres)",
            self.campo_autenticacao
        )

        self.campo_data = t.entrada(pagamento, "DD/MM/AAAA")
        self._campo(pagamento, 2, 0, "Data do pagamento", self.campo_data)
        self.campo_data.insert(0, date.today().strftime("%d/%m/%Y"))

        self.dica_data = ctk.CTkLabel(
            pagamento,
            text="Preenchida com a data de hoje",
            font=t.FONTE_PEQUENA,
            text_color=t.COR_DISCRETO,
            anchor="w"
        )
        self.dica_data.grid(row=5, column=1, sticky="w", padx=6)

        self.atualizar_opcoes_formulario()
        self._ao_mudar_pagamento()

        # ---------------------------------
        # MÁSCARAS E COMPORTAMENTOS
        # ---------------------------------

        self.campo_cpf.bind(
            "<KeyRelease>",
            lambda e: self._aplicar_mascara(self.campo_cpf, mascarar_cpf, e)
        )
        self.campo_data.bind(
            "<KeyRelease>",
            lambda e: self._aplicar_mascara(self.campo_data, mascarar_data, e)
        )
        self.campo_data.bind(
            "<FocusOut>",
            lambda e: self._aplicar_mascara(self.campo_data, mascarar_data),
            add="+"
        )
        self.campo_valor.bind("<FocusOut>", self._normalizar_valor, add="+")

        # Enter avança para o próximo campo
        self.ordem_campos = [
            self.campo_nome,
            self.campo_cpf,
            self.campo_codigo,
            self.campo_valor,
            self.campo_autenticacao,
            self.campo_data
        ]

        for campo in self.ordem_campos:
            campo.bind("<Return>", self._proximo_campo)
            campo.bind("<Key>", lambda e, c=campo: self._limpar_erro(c), add="+")

    def _aplicar_mascara(self, campo, funcao, evento=None):

        # Não interfere na navegação por setas/Tab
        if evento is not None and evento.keysym in (
            "Left", "Right", "Home", "End", "Tab", "Shift_L", "Shift_R"
        ):
            return

        texto = campo.get()
        formatado = funcao(texto)

        if texto != formatado:
            campo.delete(0, "end")
            campo.insert(0, formatado)

    def _normalizar_valor(self, _evento=None):

        texto = self.campo_valor.get().strip()

        if texto:
            novo = normalizar_valor_digitado(texto)

            if novo != texto:
                self.campo_valor.delete(0, "end")
                self.campo_valor.insert(0, novo)

    def _filtrar_autenticacao(self, *_args):

        codigo = self.variavel_autenticacao.get()
        filtrado = filtrar_autenticacao(codigo)

        if codigo != filtrado:
            self.variavel_autenticacao.set(filtrado)

    def _ao_mudar_pagamento(self, _opcao=None):

        self._limpar_erro(self.menu_pagamento)

        if self.menu_pagamento.get() in self.pagamentos_com_autenticacao:
            self.rotulo_autenticacao.grid()
            self.campo_autenticacao.grid()
        else:
            self.rotulo_autenticacao.grid_remove()
            self.campo_autenticacao.grid_remove()
            self.variavel_autenticacao.set("")
            self._limpar_erro(self.campo_autenticacao)

    def _proximo_campo(self, evento):

        visiveis = [c for c in self.ordem_campos if c.winfo_ismapped()]

        try:
            indice = visiveis.index(evento.widget.master)
        except ValueError:
            try:
                indice = visiveis.index(evento.widget)
            except ValueError:
                return "break"

        if indice + 1 < len(visiveis):
            visiveis[indice + 1].focus_set()

        return "break"

    # ---------------------------------
    # DESTAQUE DE ERROS
    # ---------------------------------

    def _marcar_erro(self, widget):

        widget._com_erro = True

        if isinstance(widget, ctk.CTkEntry):
            widget.configure(border_color=t.COR_ERRO, border_width=2)
            widget.focus_set()
        else:
            widget.configure(button_color=t.COR_ERRO, fg_color=t.COR_ERRO_FUNDO)

    def _limpar_erro(self, widget):

        if not getattr(widget, "_com_erro", False):
            return

        widget._com_erro = False

        if isinstance(widget, ctk.CTkEntry):
            focado = widget.focus_get() in (widget, getattr(widget, "_entry", None))
            widget.configure(
                border_color=t.COR_PRINCIPAL if focado else t.COR_BORDA,
                border_width=2 if focado else 1
            )
        else:
            widget.configure(button_color=t.COR_PRINCIPAL, fg_color=t.COR_CAMPOS)

    def _limpar_todos_erros(self):

        for widget in (
            *self.ordem_campos,
            self.menu_plano,
            self.menu_pagamento,
            self.menu_consultor
        ):
            self._limpar_erro(widget)

    # =====================================
    # CONSULTORES
    # =====================================

    def atualizar_consultores_formulario(self):

        from consultores import listar_consultores

        nomes_ativos = [registro[1] for registro in listar_consultores()]

        valor_atual = self.menu_consultor.get()

        self.menu_consultor.configure(
            values=[TEXTO_SELECIONE_CONSULTOR, *nomes_ativos],
            command=lambda _v: self._limpar_erro(self.menu_consultor)
        )

        # Mantém a seleção somente se o consultor continuar ativo
        if valor_atual not in nomes_ativos:
            self.menu_consultor.set(TEXTO_SELECIONE_CONSULTOR)

    # =====================================
    # PLANOS E FORMAS DE PAGAMENTO
    # =====================================

    def atualizar_opcoes_formulario(self):
        """
        Carrega planos e formas de pagamento ativos
        (editáveis em Configurações > Planos e pagamentos).
        """

        from opcoes import nomes_ativos, pagamentos_com_autenticacao

        self.pagamentos_com_autenticacao = pagamentos_com_autenticacao()

        for menu, tipo, texto_padrao in (
            (self.menu_plano, "plano", TEXTO_SELECIONE_PLANO),
            (self.menu_pagamento, "pagamento", TEXTO_SELECIONE_PAGAMENTO),
        ):
            nomes = nomes_ativos(tipo)
            atual = menu.get()
            menu.configure(values=[texto_padrao, *nomes])

            # Mantém a seleção somente se a opção continuar ativa
            if atual not in nomes:
                menu.set(texto_padrao)

        self._ao_mudar_pagamento()

    # =====================================
    # VALIDAÇÃO E CONFERÊNCIA
    # =====================================

    def _avisar(self, widget, titulo, mensagem, erro=False):

        self._marcar_erro(widget)

        if erro:
            messagebox.showerror(titulo, mensagem, parent=self.janela)
        else:
            messagebox.showwarning(titulo, mensagem, parent=self.janela)

        if isinstance(widget, ctk.CTkEntry):
            widget.focus_set()

        return None

    def coletar_dados(self):
        """
        Valida o formulário (mesmas regras da versão 2.1.2) e
        devolve os dados prontos para o banco, ou None.
        O primeiro campo com problema fica destacado em vermelho.
        """

        self._limpar_todos_erros()

        nome = " ".join(self.campo_nome.get().split())
        cpf = self.campo_cpf.get().strip()
        plano = self.menu_plano.get()
        valor = self.campo_valor.get().strip()
        pagamento = self.menu_pagamento.get()
        codigo = self.campo_codigo.get().strip()
        data_pg = self.campo_data.get().strip()
        consultor = self.menu_consultor.get()

        # Campos obrigatórios (aponta o primeiro vazio)
        obrigatorios = [
            (nome, self.campo_nome, "Nome completo"),
            (cpf, self.campo_cpf, "CPF"),
            (codigo, self.campo_codigo, "Código do aluno"),
            (valor, self.campo_valor, "Valor pago"),
            (data_pg, self.campo_data, "Data do pagamento"),
        ]

        for conteudo, widget, nome_campo in obrigatorios:
            if not conteudo:
                return self._avisar(
                    widget,
                    "Campo obrigatório",
                    f"Preencha o campo \"{nome_campo}\"."
                )

        if not validar_cpf(cpf):
            return self._avisar(
                self.campo_cpf,
                "CPF inválido",
                "O CPF informado não é válido. Confira os números.",
                erro=True
            )

        valor_convertido = validar_valor(valor)

        if valor_convertido is None:
            return self._avisar(
                self.campo_valor,
                "Valor inválido",
                "Informe um valor maior que zero.\n"
                "Exemplos: 9,90 · 150 · 1.250,00",
                erro=True
            )

        data_validada = validar_data(data_pg)

        if data_validada is None:
            return self._avisar(
                self.campo_data,
                "Data inválida",
                "Informe uma data válida no formato DD/MM/AAAA, "
                "sem utilizar datas futuras.",
                erro=True
            )

        if plano == TEXTO_SELECIONE_PLANO:
            return self._avisar(
                self.menu_plano,
                "Plano obrigatório",
                "Selecione o plano do aluno."
            )

        if pagamento == TEXTO_SELECIONE_PAGAMENTO:
            return self._avisar(
                self.menu_pagamento,
                "Pagamento obrigatório",
                "Selecione a forma de pagamento."
            )

        codigo_autenticacao = self.variavel_autenticacao.get().strip()

        if pagamento in self.pagamentos_com_autenticacao:

            if not validar_autenticacao(codigo_autenticacao):
                return self._avisar(
                    self.campo_autenticacao,
                    "Autenticação inválida",
                    f"Informe de {AUTENTICACAO_MIN} a {AUTENTICACAO_MAX} "
                    "caracteres (letras ou números) do código de "
                    "autenticação do comprovante."
                )
        else:
            codigo_autenticacao = ""

        if consultor == TEXTO_SELECIONE_CONSULTOR:
            return self._avisar(
                self.menu_consultor,
                "Consultor obrigatório",
                "Selecione o consultor responsável."
            )

        return {
            "nome": nome,
            "cpf": somente_digitos(cpf),
            "codigo_aluno": codigo,
            "plano": plano,
            "valor_centavos": valor_para_centavos(valor_convertido),
            "forma_pagamento": pagamento,
            "data_pagamento": data_validada.isoformat(),
            "consultor": consultor,
            "codigo_autenticacao": codigo_autenticacao
        }

    @staticmethod
    def linhas_resumo(dados):

        linhas = [
            ("Aluno", dados["nome"]),
            ("CPF", formatar_cpf(dados["cpf"])),
            ("Código do aluno", dados["codigo_aluno"]),
            ("Plano", dados["plano"]),
            ("Valor", formatar_reais(dados["valor_centavos"])),
            ("Pagamento", dados["forma_pagamento"]),
        ]

        if dados["codigo_autenticacao"]:
            linhas.append(("Autenticação", dados["codigo_autenticacao"]))

        linhas += [
            ("Data do pagamento", date.fromisoformat(
                dados["data_pagamento"]).strftime("%d/%m/%Y")),
            ("Consultor", dados["consultor"]),
        ]

        return linhas

    def conferir_dados(self):

        dados = self.coletar_dados()

        if dados is None:
            return None

        from dialogos import mostrar_resumo

        mostrar_resumo(
            self.janela,
            "Conferência do recibo",
            self.linhas_resumo(dados)
        )

        return dados

    # =====================================
    # SALVAR E GERAR PDF
    # =====================================

    def salvar_recibo(self):

        # Impede cliques simultâneos
        if self.salvamento_em_andamento:
            return

        dados = self.coletar_dados()

        if dados is None:
            return

        from dialogos import mostrar_resumo

        aviso = (
            "Confira os dados. Depois de salvo, o recibo "
            "fica registrado no histórico."
        )
        alerta = self._alerta_duplicidade(dados)

        # Confirma o lançamento mostrando os dados
        confirmar = mostrar_resumo(
            self.janela,
            "Confirmar lançamento",
            self.linhas_resumo(dados),
            texto_confirmar="Salvar mesmo assim" if alerta else "Salvar e gerar PDF",
            texto_cancelar="Voltar e corrigir",
            aviso=aviso,
            alerta=alerta
        )

        if not confirmar:
            return

        self.salvamento_em_andamento = True
        self.botao_salvar.configure(state="disabled", text="Salvando...")
        self.janela.update_idletasks()

        try:
            self._executar_salvamento(dados)

        except Exception as erro:
            log.exception("Falha ao salvar recibo")
            messagebox.showerror(
                "Erro ao salvar",
                f"Não foi possível concluir o salvamento:\n{erro}",
                parent=self.janela
            )

        finally:
            self.salvamento_em_andamento = False
            self.botao_salvar.configure(
                state="normal",
                text="SALVAR E GERAR RECIBO"
            )

    def _alerta_duplicidade(self, dados):
        """
        Avisa (sem impedir) quando já existe recibo com o mesmo
        CPF, valor e data de pagamento nos últimos 90 dias.
        """

        from database import buscar_duplicados

        try:
            iguais = buscar_duplicados(
                dados["cpf"], dados["valor_centavos"], dados["data_pagamento"]
            )
        except Exception:
            log.exception("Falha ao verificar duplicidade")
            return None

        if not iguais:
            return None

        lista = ", ".join(
            f"REC-{r['id']:06d} (emitido em "
            f"{datetime.fromisoformat(r['emitido_em']):%d/%m %H:%M})"
            for r in iguais
        )

        return (
            "⚠ Possível duplicidade: já existe recibo com o mesmo CPF, "
            f"valor e data de pagamento: {lista}.\n"
            "Se este é um novo lançamento correto (ex.: correção de um "
            "recibo errado), pode salvar normalmente."
        )

    def _executar_salvamento(self, dados):

        from database import inserir_recibo
        from backup import criar_backup
        from receipt_pdf import criar_pdf

        # Salva no banco SQLite
        id_recibo = inserir_recibo(**dados)
        numero = f"REC-{id_recibo:06d}"

        # Atualiza o backup após salvar o recibo
        try:
            if criar_backup() is None:
                messagebox.showwarning(
                    "Aviso de backup",
                    f"O recibo {numero} foi salvo, "
                    "mas o backup não foi atualizado.\n\n"
                    "Não salve novamente o recibo.",
                    parent=self.janela
                )
        except Exception as erro:
            log.exception("Falha no backup após salvar")
            messagebox.showwarning(
                "Erro no backup",
                f"O recibo {numero} foi salvo, "
                f"mas houve uma falha no backup:\n{erro}\n\n"
                "Não salve novamente o recibo.",
                parent=self.janela
            )

        self._atualizar_status_backup()

        # Gera o PDF
        try:
            caminho_pdf = criar_pdf(id_recibo)

            if caminho_pdf is None:
                raise RuntimeError("Recibo não localizado após o salvamento.")

        except Exception as erro:
            log.exception("PDF não gerado para %s", numero)

            # O recibo já existe: o formulário é limpo para
            # evitar que seja salvo em duplicidade.
            self.limpar_formulario()
            self._definir_status(f"{numero} salvo, mas o PDF não foi gerado.", t.COR_AVISO)

            messagebox.showwarning(
                "Recibo salvo, PDF não gerado",
                f"O recibo {numero} foi salvo no banco.\n\n"
                f"Erro ao gerar PDF:\n{erro}\n\n"
                "Não salve novamente. Use o Histórico "
                "para gerar o PDF deste recibo.",
                parent=self.janela
            )
            return

        self.limpar_formulario()
        self._definir_status(
            f"✔ Recibo {numero} gerado às {datetime.now():%H:%M}.",
            t.COR_SUCESSO
        )

        messagebox.showinfo(
            "Recibo gerado",
            f"Recibo {numero} salvo com sucesso!\n\n"
            "O documento PDF será aberto.",
            parent=self.janela
        )

        try:
            t.abrir_arquivo(caminho_pdf)
        except OSError as erro:
            messagebox.showwarning(
                "PDF salvo",
                "O PDF foi gerado, mas não foi possível "
                f"abri-lo automaticamente:\n{erro}\n\n"
                f"Local: {caminho_pdf}",
                parent=self.janela
            )

    # =====================================
    # LIMPEZA DO FORMULÁRIO
    # =====================================

    def limpar_formulario(self):

        self._limpar_todos_erros()

        for campo in (
            self.campo_nome,
            self.campo_cpf,
            self.campo_valor,
            self.campo_codigo,
            self.campo_data
        ):
            campo.delete(0, "end")

        self.campo_data.insert(0, date.today().strftime("%d/%m/%Y"))

        self.menu_plano.set(TEXTO_SELECIONE_PLANO)
        self.menu_pagamento.set(TEXTO_SELECIONE_PAGAMENTO)
        self._ao_mudar_pagamento()
        self.menu_consultor.set(TEXTO_SELECIONE_CONSULTOR)

        self.campo_nome.focus_set()

    def _formulario_preenchido(self):

        return any((
            self.campo_nome.get().strip(),
            self.campo_cpf.get().strip(),
            self.campo_codigo.get().strip(),
            self.campo_valor.get().strip(),
            self.menu_plano.get() != TEXTO_SELECIONE_PLANO,
            self.menu_pagamento.get() != TEXTO_SELECIONE_PAGAMENTO,
        ))

    def limpar_com_confirmacao(self):

        if self._formulario_preenchido() and not messagebox.askyesno(
            "Limpar formulário",
            "Deseja apagar os dados digitados?",
            parent=self.janela
        ):
            return

        self.limpar_formulario()

    # =====================================
    # BARRA DE AÇÕES E RODAPÉ
    # =====================================

    def _montar_acoes(self):

        acoes = ctk.CTkFrame(self.janela, fg_color="transparent")
        acoes.pack(fill="x", padx=22, pady=(4, 6))

        t.botao(
            acoes,
            "Limpar",
            self.limpar_com_confirmacao,
            estilo="neutro",
            width=110,
            height=50
        ).pack(side="left")

        t.botao(
            acoes,
            "Conferir dados",
            self.conferir_dados,
            estilo="principal",
            width=170,
            height=50
        ).pack(side="left", padx=(10, 0))

        self.botao_salvar = t.botao(
            acoes,
            "SALVAR E GERAR RECIBO",
            self.salvar_recibo,
            estilo="destaque",
            font=t.FONTE_BOTAO_GRANDE,
            height=50
        )
        self.botao_salvar.pack(side="left", fill="x", expand=True, padx=(10, 0))

    def _montar_rodape(self):

        rodape = ctk.CTkFrame(self.janela, fg_color=t.COR_PAINEL, corner_radius=0, height=28)
        rodape.pack(fill="x", side="bottom")

        self.status_mensagem = ctk.CTkLabel(
            rodape,
            text="Campos com * são obrigatórios  ·  Enter avança  ·  Ctrl+S salva",
            font=t.FONTE_PEQUENA,
            text_color=t.COR_DISCRETO,
            anchor="w"
        )
        self.status_mensagem.pack(side="left", padx=14, pady=4)

        self.status_backup = ctk.CTkLabel(
            rodape,
            text="",
            font=t.FONTE_PEQUENA,
            text_color=t.COR_DISCRETO,
            anchor="e"
        )
        self.status_backup.pack(side="right", padx=14)

    def _definir_status(self, texto, cor=t.COR_DISCRETO):

        self.status_mensagem.configure(text=texto, text_color=cor)

    def _atualizar_status_backup(self):

        from backup import ultimo_backup

        try:
            info = ultimo_backup()
        except OSError:
            info = None

        if info is None:
            texto = "Backup: nenhum ainda"
        else:
            texto = f"Último backup: {info[1]:%d/%m %H:%M}"

        self.status_backup.configure(
            text=f"{texto}  ·  Histórico de {DIAS_RETENCAO} dias  ·  v{VERSAO_SOFTWARE}"
        )

    def _atalhos(self):

        self.janela.bind("<Control-s>", lambda e: self.salvar_recibo())
        self.janela.bind("<Control-S>", lambda e: self.salvar_recibo())
        self.janela.bind("<Control-h>", lambda e: self.abrir_historico())
        self.janela.bind("<F5>", lambda e: self.conferir_dados())

    # =====================================
    # JANELAS AUXILIARES
    # =====================================

    def abrir_configuracoes(self):

        # Se a janela já estiver aberta, apenas traz para frente
        if self.tela_configuracoes is not None and self.tela_configuracoes.winfo_exists():
            t.trazer_para_frente(self.tela_configuracoes)
            return

        from tela_admin import abrir_tela_admin

        tela = abrir_tela_admin(self.janela, ao_restaurar=self.recarregar_dados)

        if tela is None:
            return

        self.tela_configuracoes = tela

        def fechar_configuracoes():
            try:
                self.recarregar_dados()
            finally:
                self.tela_configuracoes = None
                tela.destroy()

        tela.protocol("WM_DELETE_WINDOW", fechar_configuracoes)

    def abrir_historico(self):

        if self.tela_historico is not None and self.tela_historico.winfo_exists():
            t.trazer_para_frente(self.tela_historico)
            return

        from tela_historico import abrir_historico

        self.tela_historico = abrir_historico(self.janela)

    # =====================================
    # EXECUÇÃO
    # =====================================

    def executar(self):
        self.janela.mainloop()


def main():

    import instancia_unica

    # Opção J: somente uma cópia do programa aberta por vez
    if not instancia_unica.adquirir():
        log.info("Programa já aberto; trazendo a janela existente.")
        instancia_unica.avisar_ja_aberto()
        return

    log.info("Iniciando %s %s", NOME_SOFTWARE, VERSAO_SOFTWARE)

    app = AplicativoRecibos()
    app.executar()


if __name__ == "__main__":
    main()
