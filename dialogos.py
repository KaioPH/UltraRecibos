
"""
Janelas de diálogo personalizadas (resumo do recibo).
"""

import customtkinter as ctk

import tema as t


def mostrar_resumo(
    pai,
    titulo,
    linhas,
    texto_confirmar=None,
    texto_cancelar="Fechar",
    aviso=None,
    alerta=None
):
    """
    Exibe os dados do recibo em formato de tabela.

    - linhas: lista de (rótulo, valor)
    - texto_confirmar: se informado, mostra o botão de confirmação
      e a função retorna True somente se ele for clicado.
    """

    resultado = {"confirmado": False}

    dialogo = ctk.CTkToplevel(pai)
    dialogo.title(titulo)
    dialogo.configure(fg_color=t.COR_FUNDO)
    dialogo.resizable(False, False)
    dialogo.transient(pai)
    t.aplicar_icone(dialogo)

    quadro, conteudo = t.cartao(dialogo, titulo)
    quadro.pack(fill="both", expand=True, padx=16, pady=(16, 8))

    conteudo.grid_columnconfigure(1, weight=1)

    for linha, (nome, valor) in enumerate(linhas):

        ctk.CTkLabel(
            conteudo,
            text=nome,
            font=t.FONTE_ROTULO,
            text_color=t.COR_SECUNDARIO,
            anchor="w"
        ).grid(row=linha, column=0, sticky="w", padx=(0, 16), pady=3)

        ctk.CTkLabel(
            conteudo,
            text=str(valor),
            font=t.fonte(13, negrito=nome.startswith("Valor")),
            text_color=t.COR_TEXTO,
            anchor="w",
            justify="left",
            wraplength=360
        ).grid(row=linha, column=1, sticky="w", pady=3)

    if alerta:
        ctk.CTkLabel(
            dialogo,
            text=alerta,
            font=t.fonte(12, True),
            text_color=t.COR_TEXTO_ESCURO,
            fg_color=t.COR_AVISO_FUNDO,
            corner_radius=8,
            wraplength=480,
            justify="left",
            anchor="w"
        ).pack(fill="x", padx=16, pady=(0, 6), ipadx=10, ipady=8)

    if aviso:
        ctk.CTkLabel(
            dialogo,
            text=aviso,
            font=t.FONTE_PEQUENA,
            text_color=t.COR_SECUNDARIO,
            wraplength=480,
            justify="left"
        ).pack(fill="x", padx=20, pady=(0, 4))

    barra = ctk.CTkFrame(dialogo, fg_color="transparent")
    barra.pack(fill="x", padx=16, pady=(4, 16))

    def confirmar(_evento=None):
        resultado["confirmado"] = True
        fechar()

    def fechar(_evento=None):
        try:
            dialogo.grab_release()
        except Exception:
            pass
        dialogo.destroy()

    if texto_confirmar:

        t.botao(
            barra,
            texto_confirmar,
            confirmar,
            estilo="destaque",
            height=42
        ).pack(side="right")

        t.botao(
            barra,
            texto_cancelar,
            fechar,
            estilo="neutro",
            height=42
        ).pack(side="right", padx=(0, 8))

        dialogo.bind("<Return>", confirmar)

    else:
        t.botao(barra, texto_cancelar, fechar, height=40).pack(side="right")
        dialogo.bind("<Return>", fechar)

    dialogo.bind("<Escape>", fechar)
    dialogo.protocol("WM_DELETE_WINDOW", fechar)

    dialogo.update_idletasks()
    escala = dialogo._get_window_scaling() or 1.0
    t.centralizar(
        dialogo,
        max(520, int(dialogo.winfo_reqwidth() / escala)),
        int(dialogo.winfo_reqheight() / escala) + 10,
        pai
    )

    t.trazer_para_frente(dialogo)

    def capturar():
        try:
            dialogo.grab_set()
        except Exception:
            dialogo.after(100, capturar)

    dialogo.after(150, capturar)
    pai.wait_window(dialogo)

    return resultado["confirmado"]
