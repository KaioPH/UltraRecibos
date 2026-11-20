
"""
Configurações administrativas: empresa, logotipo,
consultores e informações do sistema (backup, pastas, versão).
"""

from tkinter import messagebox, filedialog

import customtkinter as ctk
from PIL import Image

import tema as t

from consultores import (
    inicializar_consultores,
    listar_consultores,
    cadastrar_consultor,
    alterar_consultor,
    alterar_status_consultor
)
from empresa_config import (
    carregar_empresa,
    salvar_empresa,
    obter_logo_empresa,
    salvar_logo_empresa,
    remover_logo_empresa
)
from configuracoes import (
    RAZAO_SOCIAL,
    CNPJ_EMPRESA,
    CIDADE_EMPRESA,
    NOME_SOFTWARE,
    VERSAO_SOFTWARE,
    DESENVOLVEDOR,
    DIAS_RETENCAO
)
from registro import obter_logger
from validacoes import formatar_cnpj


log = obter_logger("admin")


# =========================================
# PAINEL DE CONFIGURAÇÕES
# =========================================

def abrir_tela_admin(janela, ao_restaurar=None):

    inicializar_consultores()

    tela = ctk.CTkToplevel(janela)
    tela.title("Ultra Recibos - Configurações")
    tela.configure(fg_color=t.COR_FUNDO)
    tela.minsize(700, 500)
    t.aplicar_icone(tela)
    t.centralizar(tela, 900, 640, janela)

    abas = ctk.CTkTabview(
        tela,
        fg_color=t.COR_PAINEL,
        segmented_button_fg_color=t.COR_PAINEL_CLARO,
        segmented_button_selected_color=t.COR_PRINCIPAL,
        segmented_button_selected_hover_color=t.COR_PRINCIPAL_HOVER,
        segmented_button_unselected_color=t.COR_PAINEL_CLARO,
        text_color=t.COR_TEXTO,
        corner_radius=12
    )
    abas.pack(fill="both", expand=True, padx=18, pady=18)

    _aba_empresa(tela, abas.add("Empresa"))
    _aba_consultores(tela, abas.add("Consultores"))
    _aba_opcoes(tela, abas.add("Planos e pagamentos"))
    _aba_aparencia(tela, abas.add("Aparência"))
    _aba_sistema(tela, abas.add("Sistema"), ao_restaurar)

    abas._segmented_button.configure(font=t.FONTE_BOTAO)

    t.trazer_para_frente(tela)

    return tela


# =========================================
# ABA: EMPRESA
# =========================================

def _aba_empresa(tela, aba):

    area = ctk.CTkScrollableFrame(aba, fg_color=t.COR_PAINEL)
    area.pack(fill="both", expand=True)
    area.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        area,
        text="Dados da empresa emissora",
        font=t.FONTE_SECAO,
        text_color=t.COR_TEXTO,
        anchor="w"
    ).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 0))

    ctk.CTkLabel(
        area,
        text=(
            "Estes dados são gravados em cada recibo no momento da emissão. "
            "Alterações valem apenas para os próximos recibos."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_DISCRETO,
        anchor="w",
        justify="left",
        wraplength=640
    ).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))

    # Carrega os dados atuais. Se o arquivo estiver danificado,
    # a tela continua aberta com os dados padrão para que o
    # administrador possa corrigir e salvar novamente.
    try:
        empresa = carregar_empresa()

    except (OSError, ValueError) as erro:
        log.warning("Configuração da empresa inválida: %s", erro)
        messagebox.showwarning(
            "Configuração da empresa",
            f"{erro}\n\nOs dados padrão foram carregados. "
            "Confira e clique em \"Salvar dados da empresa\".",
            parent=tela
        )
        empresa = None

    if empresa is None:
        empresa = {
            "razao_social": RAZAO_SOCIAL,
            "cnpj": CNPJ_EMPRESA,
            "cidade": CIDADE_EMPRESA
        }

    formulario = ctk.CTkFrame(area, fg_color=t.COR_PAINEL_CLARO, corner_radius=10)
    formulario.grid(row=2, column=0, sticky="ew", padx=8, pady=4)
    formulario.grid_columnconfigure(0, weight=1)

    def criar_campo(linha, texto, valor, placeholder=""):
        t.rotulo(formulario, texto, obrigatorio=True).grid(
            row=linha * 2, column=0, sticky="w", padx=16, pady=(10, 2)
        )
        campo = t.entrada(formulario, placeholder)
        campo.grid(row=linha * 2 + 1, column=0, sticky="ew", padx=16)
        campo.insert(0, valor)
        return campo

    campo_razao = criar_campo(0, "Razão social / nome do estabelecimento", empresa["razao_social"])
    campo_cnpj = criar_campo(1, "CNPJ", formatar_cnpj(empresa["cnpj"]), "00.000.000/0000-00")
    campo_cidade = criar_campo(2, "Cidade", empresa["cidade"])

    def salvar_dados_empresa():

        try:
            dados = salvar_empresa(
                campo_razao.get(),
                campo_cnpj.get(),
                campo_cidade.get()
            )

        except (ValueError, OSError) as erro:
            messagebox.showerror("Erro ao salvar", str(erro), parent=tela)
            return

        campo_cnpj.delete(0, "end")
        campo_cnpj.insert(0, formatar_cnpj(dados["cnpj"]))

        messagebox.showinfo(
            "Configurações salvas",
            "Dados da empresa armazenados com sucesso.",
            parent=tela
        )

    t.botao(
        formulario,
        "Salvar dados da empresa",
        salvar_dados_empresa,
        width=240,
        height=40
    ).grid(row=6, column=0, sticky="e", padx=16, pady=14)

    # ---------------------------------
    # LOGOTIPO
    # ---------------------------------

    ctk.CTkLabel(
        area,
        text="Logotipo do estabelecimento",
        font=t.FONTE_SECAO,
        text_color=t.COR_TEXTO,
        anchor="w"
    ).grid(row=3, column=0, sticky="w", padx=8, pady=(16, 0))

    ctk.CTkLabel(
        area,
        text=(
            "Aparece no topo do programa e nos próximos recibos. "
            "Formatos: PNG, JPG ou WEBP (até 10 MB)."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_DISCRETO,
        anchor="w"
    ).grid(row=4, column=0, sticky="w", padx=8, pady=(0, 6))

    quadro_logo = ctk.CTkFrame(area, fg_color=t.COR_PAINEL_CLARO, corner_radius=10)
    quadro_logo.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 10))
    quadro_logo.grid_columnconfigure(0, weight=1)

    previa_logo = ctk.CTkLabel(
        quadro_logo,
        text="Nenhum logotipo personalizado",
        width=260,
        height=90,
        fg_color=t.COR_CAMPOS,
        corner_radius=8,
        text_color=t.COR_SECUNDARIO
    )
    previa_logo.grid(row=0, column=0, rowspan=2, sticky="w", padx=16, pady=14)

    def atualizar_previa_logo():

        caminho = obter_logo_empresa()

        if caminho is None:
            previa_logo.configure(image=None, text="Nenhum logotipo personalizado")
            previa_logo.imagem_atual = None
            return

        try:
            with Image.open(caminho) as imagem:
                imagem = imagem.convert("RGBA")
                imagem.thumbnail((240, 80))

            logo_ctk = ctk.CTkImage(light_image=imagem, dark_image=imagem, size=imagem.size)
            previa_logo.configure(image=logo_ctk, text="")

            # Mantém a referência da imagem
            previa_logo.imagem_atual = logo_ctk

        except (OSError, ValueError):
            previa_logo.configure(image=None, text="Não foi possível carregar a imagem")

    def selecionar_logo():

        caminho = filedialog.askopenfilename(
            parent=tela,
            title="Selecionar logotipo",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.webp")]
        )

        if not caminho:
            return

        try:
            salvar_logo_empresa(caminho)
            atualizar_previa_logo()
            messagebox.showinfo(
                "Logotipo salvo",
                "O logotipo foi salvo com sucesso.",
                parent=tela
            )

        except (ValueError, OSError) as erro:
            messagebox.showerror("Erro no logotipo", str(erro), parent=tela)

    def remover_logo():

        if obter_logo_empresa() is None:
            return

        if not messagebox.askyesno(
            "Remover logotipo",
            "Remover o logotipo personalizado?\n\n"
            "Os próximos recibos serão emitidos sem logotipo. "
            "Recibos já emitidos não são alterados.",
            parent=tela
        ):
            return

        try:
            remover_logo_empresa()
        except OSError as erro:
            messagebox.showerror("Erro no logotipo", str(erro), parent=tela)
            return

        atualizar_previa_logo()

    t.botao(quadro_logo, "Selecionar logotipo", selecionar_logo, estilo="roxo", width=200).grid(
        row=0, column=1, sticky="se", padx=16, pady=(14, 4)
    )
    t.botao(quadro_logo, "Remover", remover_logo, estilo="neutro", width=200).grid(
        row=1, column=1, sticky="ne", padx=16, pady=(4, 14)
    )

    atualizar_previa_logo()


# =========================================
# ABA: CONSULTORES
# =========================================

def _aba_consultores(tela, aba):

    barra = ctk.CTkFrame(aba, fg_color="transparent")
    barra.pack(fill="x", padx=8, pady=(8, 4))

    campo_novo = t.entrada(barra, "Nome completo do novo consultor")
    campo_novo.pack(side="left", fill="x", expand=True)

    lista = ctk.CTkScrollableFrame(aba, fg_color=t.COR_FUNDO, corner_radius=10)
    lista.pack(fill="both", expand=True, padx=8, pady=8)

    ctk.CTkLabel(
        aba,
        text=(
            "Consultores inativos não aparecem no formulário, mas continuam "
            "nos recibos já emitidos. Renomear não altera recibos anteriores."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_DISCRETO,
        wraplength=660,
        justify="left",
        anchor="w"
    ).pack(fill="x", padx=10, pady=(0, 6))

    def atualizar_lista():

        for componente in lista.winfo_children():
            componente.destroy()

        registros = listar_consultores(apenas_ativos=False)

        # Ativos primeiro, depois inativos
        registros = sorted(registros, key=lambda r: (not r[2], r[1].casefold()))

        for id_consultor, nome, ativo in registros:

            linha = ctk.CTkFrame(lista, fg_color=t.COR_CAMPOS, corner_radius=8)
            linha.pack(fill="x", padx=4, pady=3)

            ctk.CTkLabel(
                linha,
                text=nome,
                font=t.fonte(13, bool(ativo)),
                text_color=t.COR_TEXTO if ativo else t.COR_DISCRETO,
                anchor="w"
            ).pack(side="left", fill="x", expand=True, padx=12, pady=8)

            ctk.CTkLabel(
                linha,
                text="Ativo" if ativo else "Inativo",
                font=t.fonte(11, True),
                width=70,
                height=24,
                corner_radius=12,
                fg_color=t.COR_SUCESSO_FUNDO if ativo else t.COR_NEUTRO,
                text_color=t.COR_SUCESSO if ativo else t.COR_SECUNDARIO
            ).pack(side="left", padx=6)

            t.botao(
                linha,
                "Renomear",
                lambda i=id_consultor, n=nome: editar(i, n),
                estilo="neutro",
                width=90,
                height=32
            ).pack(side="left", padx=4)

            t.botao(
                linha,
                "Desativar" if ativo else "Reativar",
                lambda i=id_consultor, a=ativo: mudar_status(i, not a),
                estilo="roxo" if ativo else "principal",
                width=96,
                height=32
            ).pack(side="left", padx=(4, 10), pady=6)

    def editar(identificador, nome_atual):

        dialogo = ctk.CTkInputDialog(
            title="Renomear consultor",
            text=f"Nome atual: {nome_atual}\n\nNovo nome completo:"
        )
        t.aplicar_icone(dialogo)

        novo_nome = dialogo.get_input()

        if novo_nome is None:
            return

        try:
            alterar_consultor(identificador, novo_nome)
        except ValueError as erro:
            messagebox.showerror("Erro", str(erro), parent=tela)
            return

        atualizar_lista()

    def mudar_status(identificador, novo_status):

        acao = "reativar" if novo_status else "desativar"

        if not messagebox.askyesno(
            "Confirmar alteração",
            f"Deseja {acao} este consultor?",
            parent=tela
        ):
            return

        try:
            alterar_status_consultor(identificador, novo_status)
        except ValueError as erro:
            messagebox.showerror("Erro", str(erro), parent=tela)
            return

        atualizar_lista()

    def adicionar_consultor(_evento=None):

        nome = campo_novo.get()

        try:
            cadastrar_consultor(nome)
        except ValueError as erro:
            messagebox.showerror("Erro", str(erro), parent=tela)
            return

        campo_novo.delete(0, "end")
        atualizar_lista()

    campo_novo.bind("<Return>", adicionar_consultor)

    t.botao(
        barra,
        "+ Adicionar",
        adicionar_consultor,
        estilo="destaque",
        width=130
    ).pack(side="left", padx=(8, 0))

    atualizar_lista()


# =========================================
# ABA: PLANOS E FORMAS DE PAGAMENTO
# =========================================

def _aba_opcoes(tela, aba):

    import opcoes

    opcoes.inicializar_opcoes()

    aba.grid_columnconfigure(0, weight=1, uniform="col")
    aba.grid_columnconfigure(1, weight=1, uniform="col")
    aba.grid_rowconfigure(1, weight=1)

    ctk.CTkLabel(
        aba,
        text=(
            "Desativar retira a opção do formulário sem alterar recibos já emitidos. "
            "Use ▲ ▼ para definir a ordem em que aparecem."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_DISCRETO,
        anchor="w"
    ).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 6))

    def coluna(indice, tipo, titulo):

        quadro = ctk.CTkFrame(aba, fg_color="transparent")
        quadro.grid(row=0, column=indice, rowspan=2, sticky="nsew", padx=6, pady=(6, 4))
        quadro.grid_columnconfigure(0, weight=1)
        quadro.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            quadro, text=titulo, font=t.FONTE_SECAO, text_color=t.COR_TEXTO, anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        barra = ctk.CTkFrame(quadro, fg_color="transparent")
        barra.grid(row=1, column=0, sticky="ew")
        barra.grid_columnconfigure(0, weight=1)

        campo = t.entrada(barra, "Novo plano" if tipo == "plano" else "Nova forma de pagamento")
        campo.grid(row=0, column=0, sticky="ew")

        exige_var = ctk.BooleanVar(value=False)

        if tipo == "pagamento":
            ctk.CTkCheckBox(
                barra,
                text="Exige código de autenticação",
                variable=exige_var,
                font=t.FONTE_PEQUENA,
                fg_color=t.COR_PRINCIPAL,
                hover_color=t.COR_PRINCIPAL_HOVER,
                checkbox_width=18,
                checkbox_height=18
            ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        lista = ctk.CTkScrollableFrame(quadro, fg_color=t.COR_FUNDO, corner_radius=10)
        lista.grid(row=2, column=0, sticky="nsew", pady=(6, 0))

        def atualizar():

            for componente in lista.winfo_children():
                componente.destroy()

            for id_opcao, nome, ativo, exige in opcoes.listar_opcoes(tipo, apenas_ativas=False):

                linha = ctk.CTkFrame(lista, fg_color=t.COR_CAMPOS, corner_radius=8)
                linha.pack(fill="x", padx=3, pady=3)

                texto = nome + ("   🔒" if exige else "")

                ctk.CTkLabel(
                    linha,
                    text=texto,
                    font=t.fonte(12, bool(ativo)),
                    text_color=t.COR_TEXTO if ativo else t.COR_DISCRETO,
                    anchor="w"
                ).pack(side="left", fill="x", expand=True, padx=(10, 4), pady=6)

                for simbolo, direcao in (("▲", -1), ("▼", 1)):
                    t.botao(
                        linha, simbolo,
                        lambda i=id_opcao, d=direcao: executar(opcoes.mover_opcao, i, d),
                        estilo="neutro", width=28, height=28
                    ).pack(side="left", padx=1)

                menu_acoes = [
                    ("Renomear", lambda i=id_opcao, n=nome: renomear(i, n)),
                    ("Desativar" if ativo else "Reativar",
                     lambda i=id_opcao, a=ativo: executar(opcoes.alterar_status_opcao, i, not a)),
                ]

                if tipo == "pagamento":
                    menu_acoes.append((
                        "Tirar autenticação" if exige else "Exigir autenticação",
                        lambda i=id_opcao, e=exige: executar(opcoes.alterar_autenticacao, i, not e)
                    ))

                seletor = ctk.CTkOptionMenu(
                    linha,
                    values=[rotulo for rotulo, _ in menu_acoes],
                    width=110,
                    height=28,
                    font=t.FONTE_PEQUENA,
                    dropdown_font=t.FONTE_PEQUENA,
                    fg_color=t.COR_ROXO,
                    button_color=t.COR_ROXO_HOVER,
                    button_hover_color=t.COR_ROXO_HOVER,
                    dynamic_resizing=False
                )
                seletor.set("Ações")
                acoes = dict(menu_acoes)
                seletor.configure(command=lambda escolha, a=acoes: a[escolha]())
                seletor.pack(side="left", padx=(4, 6), pady=4)

        def executar(funcao, *argumentos):
            try:
                funcao(*argumentos)
            except ValueError as erro:
                messagebox.showerror("Erro", str(erro), parent=tela)
            atualizar()

        def renomear(id_opcao, nome_atual):
            dialogo = ctk.CTkInputDialog(
                title="Renomear",
                text=f"Nome atual: {nome_atual}\n\nNovo nome:\n"
                     "(recibos já emitidos mantêm o nome antigo)"
            )
            novo = dialogo.get_input()
            if novo is not None:
                executar(opcoes.renomear_opcao, id_opcao, novo)

        def adicionar(_evento=None):
            try:
                opcoes.adicionar_opcao(tipo, campo.get(), exige_var.get())
            except ValueError as erro:
                messagebox.showerror("Erro", str(erro), parent=tela)
                return
            campo.delete(0, "end")
            exige_var.set(False)
            atualizar()

        campo.bind("<Return>", adicionar)
        t.botao(barra, "+ Adicionar", adicionar, estilo="destaque", width=110).grid(
            row=0, column=1, padx=(6, 0)
        )

        atualizar()

    coluna(0, "plano", "Planos")
    coluna(1, "pagamento", "Formas de pagamento")


# =========================================
# ABA: SISTEMA
# =========================================

def _aba_aparencia(tela, aba):

    from preferencias import obter_preferencia, salvar_preferencia

    ctk.CTkLabel(
        aba,
        text="Aparência do programa",
        font=t.FONTE_SECAO,
        text_color=t.COR_TEXTO,
        anchor="w"
    ).pack(fill="x", padx=14, pady=(14, 0))

    ctk.CTkLabel(
        aba,
        text=(
            "As cores oficiais da Ultra são mantidas nos dois temas; "
            "muda apenas o fundo (claro ou escuro). A alteração vale na hora "
            "e fica salva neste computador."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_DISCRETO,
        anchor="w",
        justify="left",
        wraplength=700
    ).pack(fill="x", padx=14, pady=(0, 10))

    escolha = ctk.StringVar(value=obter_preferencia("aparencia"))

    quadro = ctk.CTkFrame(aba, fg_color=t.COR_PAINEL_CLARO, corner_radius=10)
    quadro.pack(fill="x", padx=12, pady=4)

    def aplicar():
        modo = escolha.get()
        try:
            salvar_preferencia("aparencia", modo)
        except (OSError, ValueError) as erro:
            messagebox.showerror("Aparência", str(erro), parent=tela)
            return
        t.aplicar_tema(modo)

    for chave, descricao in t.MODOS_APARENCIA.items():
        ctk.CTkRadioButton(
            quadro,
            text=descricao,
            value=chave,
            variable=escolha,
            command=aplicar,
            font=t.fonte(13),
            text_color=t.COR_TEXTO,
            fg_color=t.COR_PRINCIPAL,
            hover_color=t.COR_PRINCIPAL_HOVER
        ).pack(anchor="w", padx=16, pady=9)

    ctk.CTkLabel(
        aba,
        text=(
            "\"Automático pelo horário\" funciona como no celular: tema claro durante o dia "
            "e escuro à noite, trocando sozinho. \"Seguir o Windows\" usa o modo definido em "
            "Configurações do Windows > Personalização > Cores."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_DISCRETO,
        anchor="w",
        justify="left",
        wraplength=700
    ).pack(fill="x", padx=14, pady=(10, 0))


def _aba_sistema(tela, aba, ao_restaurar=None):

    from caminhos import PASTA_DADOS, PASTA_PDFS, PASTA_BACKUPS, PASTA_LOGS
    from backup import criar_backup, ultimo_backup, listar_backups
    from database import estatisticas_banco

    area = ctk.CTkScrollableFrame(aba, fg_color=t.COR_PAINEL)
    area.pack(fill="both", expand=True)
    area.grid_columnconfigure(1, weight=1)

    linha_atual = {"n": 0}

    def titulo(texto):
        ctk.CTkLabel(
            area,
            text=texto,
            font=t.FONTE_SECAO,
            text_color=t.COR_TEXTO,
            anchor="w"
        ).grid(row=linha_atual["n"], column=0, columnspan=3, sticky="w", padx=8, pady=(12, 4))
        linha_atual["n"] += 1

    def item(nome, valor="", acao=None, texto_acao="Abrir"):
        ctk.CTkLabel(
            area,
            text=nome,
            font=t.FONTE_ROTULO,
            text_color=t.COR_SECUNDARIO,
            anchor="w"
        ).grid(row=linha_atual["n"], column=0, sticky="w", padx=(12, 16), pady=3)

        rotulo_valor = ctk.CTkLabel(
            area,
            text=valor,
            font=t.fonte(12),
            text_color=t.COR_TEXTO,
            anchor="w",
            justify="left",
            wraplength=430
        )
        rotulo_valor.grid(row=linha_atual["n"], column=1, sticky="w", pady=3)

        if acao is not None:
            t.botao(area, texto_acao, acao, estilo="neutro", width=90, height=30).grid(
                row=linha_atual["n"], column=2, padx=8, pady=3
            )

        linha_atual["n"] += 1
        return rotulo_valor

    def abrir(pasta):
        def _abrir():
            try:
                pasta.mkdir(parents=True, exist_ok=True)
                t.abrir_arquivo(pasta)
            except OSError as erro:
                messagebox.showerror("Erro", str(erro), parent=tela)
        return _abrir

    # ---------------------------------
    titulo("Programa")
    item("Versão", f"{NOME_SOFTWARE} {VERSAO_SOFTWARE}")
    item("Desenvolvedor", DESENVOLVEDOR)

    # ---------------------------------
    titulo("Banco de dados")
    rotulo_estatisticas = item("Recibos", "")
    item("Pasta de dados", str(PASTA_DADOS), abrir(PASTA_DADOS))
    item(
        "PDFs",
        f"{PASTA_PDFS}\nPDFs com mais de {DIAS_RETENCAO} dias são apagados ao abrir o "
        "programa. Os registros continuam no banco.",
        abrir(PASTA_PDFS)
    )

    # ---------------------------------
    titulo("Backup")
    rotulo_backup = item("Último backup", "")
    item("Pasta de backups", str(PASTA_BACKUPS), abrir(PASTA_BACKUPS))
    item("Registros (log)", str(PASTA_LOGS), abrir(PASTA_LOGS))

    def atualizar_informacoes():

        try:
            estat = estatisticas_banco()
            rotulo_estatisticas.configure(
                text=(
                    f"{estat['total_recibos']} no total · "
                    f"{estat['recibos_periodo']} nos últimos {DIAS_RETENCAO} dias · "
                    f"banco com {estat['tamanho_bytes'] / 1_048_576:.1f} MB".replace(".", ",")
                )
            )
        except Exception as erro:
            rotulo_estatisticas.configure(text=f"Indisponível: {erro}")

        info = ultimo_backup()

        if info is None:
            rotulo_backup.configure(text="Nenhum backup encontrado")
        else:
            rotulo_backup.configure(
                text=f"{info[1]:%d/%m/%Y %H:%M} · {len(listar_backups())} arquivo(s) diário(s)"
            )

    def backup_agora():

        if criar_backup() is None:
            messagebox.showerror(
                "Backup",
                "Não foi possível criar o backup. Consulte o log.",
                parent=tela
            )
        else:
            messagebox.showinfo("Backup", "Backup criado com sucesso.", parent=tela)

        atualizar_informacoes()
        preencher_backups()

    t.botao(area, "Fazer backup agora", backup_agora, width=200).grid(
        row=linha_atual["n"], column=0, columnspan=2, sticky="w", padx=12, pady=(10, 4)
    )
    linha_atual["n"] += 1

    ctk.CTkLabel(
        area,
        text=(
            "Recomendação: copie periodicamente a pasta de backups para um "
            "pendrive ou nuvem. Um backup no mesmo computador não protege "
            "contra defeito do disco ou perda do equipamento."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_AVISO,
        wraplength=640,
        justify="left",
        anchor="w"
    ).grid(row=linha_atual["n"], column=0, columnspan=3, sticky="w", padx=12, pady=(4, 10))
    linha_atual["n"] += 1

    # ---------------------------------
    # RESTAURAÇÃO
    # ---------------------------------

    titulo("Restaurar backup")

    ctk.CTkLabel(
        area,
        text=(
            "Use somente em emergências (banco danificado, computador novo, "
            "alteração errada). O banco atual é guardado antes da troca, "
            "permitindo desfazer."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_DISCRETO,
        wraplength=640,
        justify="left",
        anchor="w"
    ).grid(row=linha_atual["n"], column=0, columnspan=3, sticky="w", padx=12)
    linha_atual["n"] += 1

    lista_backups = ctk.CTkFrame(area, fg_color=t.COR_FUNDO, corner_radius=10)
    lista_backups.grid(row=linha_atual["n"], column=0, columnspan=3, sticky="ew", padx=8, pady=6)
    linha_atual["n"] += 1

    estado = {"todos": False}

    def preencher_backups():

        from backup import inspecionar_backup

        for componente in lista_backups.winfo_children():
            componente.destroy()

        arquivos = listar_backups()

        if not arquivos:
            ctk.CTkLabel(
                lista_backups, text="Nenhum backup disponível.",
                text_color=t.COR_SECUNDARIO
            ).pack(pady=14)
            return

        cab = ctk.CTkFrame(lista_backups, fg_color="transparent")
        cab.pack(fill="x", padx=8, pady=(6, 0))

        larguras = (150, 90, 120, 80)

        for texto, largura in zip(("Data do backup", "Recibos", "Último recibo", "Tamanho"), larguras):
            ctk.CTkLabel(
                cab, text=texto, width=largura, anchor="w",
                font=t.FONTE_ROTULO, text_color=t.COR_SECUNDARIO
            ).pack(side="left")

        exibidos = arquivos if estado["todos"] else arquivos[:10]

        for arquivo in exibidos:

            linha = ctk.CTkFrame(lista_backups, fg_color=t.COR_CAMPOS, corner_radius=8)
            linha.pack(fill="x", padx=6, pady=2)

            try:
                info = inspecionar_backup(arquivo)
                valores = (
                    f"{info['modificado_em']:%d/%m/%Y %H:%M}",
                    f"{info['total_recibos']}",
                    f"REC-{info['ultimo_id']:06d}" if info["ultimo_id"] else "—",
                    f"{info['tamanho_bytes'] / 1_048_576:.1f} MB".replace(".", ","),
                )
                valido = True
            except ValueError as erro:
                valores = (arquivo.stem[-8:], "—", str(erro)[:40], "")
                valido = False

            for texto, largura in zip(valores, larguras):
                ctk.CTkLabel(
                    linha, text=texto, width=largura, anchor="w",
                    font=t.fonte(12), text_color=t.COR_TEXTO
                ).pack(side="left", padx=(6, 0), pady=6)

            if valido:
                t.botao(
                    linha, "Restaurar",
                    lambda a=arquivo: confirmar_restauracao(a),
                    estilo="roxo", width=100, height=30
                ).pack(side="right", padx=8)

        if len(arquivos) > 10:
            t.botao(
                lista_backups,
                "Mostrar menos" if estado["todos"] else f"Mostrar todos ({len(arquivos)})",
                alternar_todos,
                estilo="neutro", width=180, height=30
            ).pack(anchor="w", padx=8, pady=6)

    def alternar_todos():
        estado["todos"] = not estado["todos"]
        preencher_backups()

    def restaurar_arquivo_externo():
        caminho = filedialog.askopenfilename(
            parent=tela,
            title="Selecionar backup do Ultra Recibos",
            filetypes=[("Banco de dados", "*.db"), ("Todos os arquivos", "*.*")]
        )
        if caminho:
            confirmar_restauracao(caminho)

    def confirmar_restauracao(caminho):

        from pathlib import Path
        from backup import inspecionar_backup, restaurar_backup, configuracao_do_backup

        try:
            info = inspecionar_backup(caminho)
            atual = estatisticas_banco()
        except Exception as erro:
            messagebox.showerror("Restaurar backup", str(erro), parent=tela)
            return

        dialogo = ctk.CTkToplevel(tela)
        dialogo.title("Confirmar restauração")
        dialogo.configure(fg_color=t.COR_FUNDO)
        dialogo.transient(tela)
        dialogo.resizable(False, False)
        t.aplicar_icone(dialogo)

        quadro, conteudo = t.cartao(dialogo, "Confirmar restauração", t.COR_ERRO)
        quadro.pack(fill="both", expand=True, padx=14, pady=(14, 6))
        conteudo.grid_columnconfigure(1, weight=1)

        diferenca = atual["total_recibos"] - info["total_recibos"]

        linhas = [
            ("Backup escolhido",
             f"{Path(caminho).name}\n{info['modificado_em']:%d/%m/%Y %H:%M} · "
             f"{info['total_recibos']} recibos"),
            ("Banco atual", f"{atual['total_recibos']} recibos"),
        ]

        if diferenca > 0:
            linhas.append((
                "Atenção",
                f"{diferenca} recibo(s) emitido(s) depois deste backup NÃO estarão "
                "no banco restaurado (continuam guardados na cópia de segurança)."
            ))

        for i, (rotulo_txt, valor) in enumerate(linhas):
            ctk.CTkLabel(
                conteudo, text=rotulo_txt, font=t.FONTE_ROTULO,
                text_color=t.COR_SECUNDARIO, anchor="nw"
            ).grid(row=i, column=0, sticky="nw", padx=(0, 12), pady=4)
            ctk.CTkLabel(
                conteudo, text=valor, font=t.fonte(12, rotulo_txt == "Atenção"),
                text_color=t.COR_AVISO if rotulo_txt == "Atenção" else t.COR_TEXTO,
                anchor="w", justify="left", wraplength=330
            ).grid(row=i, column=1, sticky="w", pady=4)

        linha = len(linhas)
        restaurar_config = ctk.BooleanVar(value=False)

        if configuracao_do_backup(caminho) is not None and Path(caminho).parent == PASTA_BACKUPS:
            ctk.CTkCheckBox(
                conteudo,
                text="Restaurar também dados da empresa e logotipo deste dia",
                variable=restaurar_config,
                font=t.FONTE_PEQUENA,
                fg_color=t.COR_PRINCIPAL
            ).grid(row=linha, column=0, columnspan=2, sticky="w", pady=(8, 0))
            linha += 1

        ctk.CTkLabel(
            conteudo,
            text="Digite RESTAURAR para confirmar:",
            font=t.FONTE_PEQUENA,
            text_color=t.COR_SECUNDARIO,
            anchor="w"
        ).grid(row=linha, column=0, columnspan=2, sticky="w", pady=(10, 2))

        campo_confirmacao = t.entrada(conteudo, "RESTAURAR")
        campo_confirmacao.grid(row=linha + 1, column=0, columnspan=2, sticky="ew")

        barra = ctk.CTkFrame(dialogo, fg_color="transparent")
        barra.pack(fill="x", padx=14, pady=(4, 14))

        def executar():

            if campo_confirmacao.get().strip().upper() != "RESTAURAR":
                messagebox.showwarning(
                    "Restaurar backup",
                    "Digite RESTAURAR para confirmar.",
                    parent=dialogo
                )
                return

            try:
                copia = restaurar_backup(caminho, restaurar_config.get())
            except Exception as erro:
                log.exception("Falha na restauração")
                messagebox.showerror(
                    "Restaurar backup",
                    f"A restauração não foi concluída:\n{erro}\n\n"
                    "O banco atual não foi alterado.",
                    parent=dialogo
                )
                return

            dialogo.destroy()

            if ao_restaurar is not None:
                ao_restaurar()

            atualizar_informacoes()
            preencher_backups()

            messagebox.showinfo(
                "Restaurar backup",
                "Backup restaurado com sucesso.\n\n"
                f"O banco anterior foi guardado em:\n{copia.name}",
                parent=tela
            )

        t.botao(barra, "Restaurar", executar, estilo="perigo", width=140).pack(side="right")
        t.botao(barra, "Cancelar", dialogo.destroy, estilo="neutro", width=110).pack(side="right", padx=8)

        dialogo.bind("<Escape>", lambda e: dialogo.destroy())
        t.centralizar(dialogo, 560, 390, tela)
        t.trazer_para_frente(dialogo)
        campo_confirmacao.focus_set()

    t.botao(
        area,
        "Restaurar de outro arquivo (pendrive)…",
        restaurar_arquivo_externo,
        estilo="neutro",
        width=300
    ).grid(row=linha_atual["n"], column=0, columnspan=3, sticky="w", padx=12, pady=(0, 14))
    linha_atual["n"] += 1

    preencher_backups()
    atualizar_informacoes()
