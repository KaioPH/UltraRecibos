
"""
Identidade visual e componentes reutilizáveis da interface.

Centraliza cores, fontes e utilitários de janela para que todas
as telas tenham a mesma aparência.
"""

import os
import subprocess
import sys

import customtkinter as ctk

from caminhos import caminho_asset


# =========================================
# CORES OFICIAIS DA ULTRA ACADEMIA
# =========================================

COR_PRINCIPAL = "#2FABAB"
COR_PRINCIPAL_HOVER = "#238989"
COR_LARANJA = "#EF8128"
COR_LARANJA_HOVER = "#D56D1D"
COR_ROXO = "#AA4894"
COR_ROXO_HOVER = "#873675"

# Cores de interface: (tema claro, tema escuro).
# O CustomTkinter escolhe automaticamente conforme a aparência ativa.
# As cores oficiais da Ultra (acima) são as mesmas nos dois temas.
COR_FUNDO = ("#EEF1F4", "#1C1F23")
COR_PAINEL = ("#FFFFFF", "#262A2F")
COR_PAINEL_CLARO = ("#F3F5F7", "#2E3338")
COR_CAMPOS = ("#F7F9FA", "#33383D")
COR_BORDA = ("#C5CDD4", "#454C53")
COR_TEXTO = ("#1C1F23", "#FFFFFF")
COR_TEXTO_ESCURO = "#171717"
COR_SECUNDARIO = ("#4A5560", "#B8C2C9")
COR_DISCRETO = ("#6B7680", "#8A949C")

# Estados
COR_ERRO = "#E5484D"
COR_ERRO_FUNDO = ("#FBE3E4", "#4A2A2C")
COR_SUCESSO = ("#1B8F52", "#3DBE7A")
COR_SUCESSO_FUNDO = ("#D7F2E3", "#1F4D3A")
COR_AVISO = ("#A86200", "#F5B544")
COR_AVISO_FUNDO = "#F5B544"
COR_NEUTRO = ("#DCE2E7", "#4A5157")
COR_NEUTRO_HOVER = ("#C9D1D8", "#5A6268")


# =========================================
# FONTES
# =========================================
# Segoe UI é a fonte padrão do Windows 10/11.

FAMILIA = "Segoe UI"


def fonte(tamanho=13, negrito=False):
    return (FAMILIA, tamanho, "bold" if negrito else "normal")


FONTE_TITULO = (FAMILIA, 24, "bold")
FONTE_SUBTITULO = (FAMILIA, 12)
FONTE_SECAO = (FAMILIA, 15, "bold")
FONTE_ROTULO = (FAMILIA, 12, "bold")
FONTE_CAMPO = (FAMILIA, 13)
FONTE_BOTAO = (FAMILIA, 13, "bold")
FONTE_BOTAO_GRANDE = (FAMILIA, 16, "bold")
FONTE_PEQUENA = (FAMILIA, 11)


# =========================================
# CONFIGURAÇÃO GERAL
# =========================================

# =========================================
# APARÊNCIA (CLARO / ESCURO / AUTOMÁTICO)
# =========================================

MODOS_APARENCIA = {
    "auto_horario": "Automático pelo horário (claro das 6h às 18h)",
    "sistema": "Seguir o Windows",
    "claro": "Sempre claro",
    "escuro": "Sempre escuro",
}

HORA_INICIO_CLARO = 6
HORA_FIM_CLARO = 18


def modo_efetivo(modo, agora=None):
    """
    Converte a preferência salva no modo do CustomTkinter.
    """

    from datetime import datetime

    if modo == "claro":
        return "light"
    if modo == "escuro":
        return "dark"
    if modo == "sistema":
        return "system"

    hora = (agora or datetime.now()).hour
    return "light" if HORA_INICIO_CLARO <= hora < HORA_FIM_CLARO else "dark"


def aplicar_tema(modo=None):
    """
    Aplica a aparência escolhida em Configurações > Aparência.
    """

    from preferencias import obter_preferencia

    if modo is None:
        modo = obter_preferencia("aparencia")

    novo = modo_efetivo(modo)

    if ctk.get_appearance_mode().lower() != novo or novo == "system":
        ctk.set_appearance_mode(novo)

    ctk.set_default_color_theme("blue")


def aplicar_icone(janela):
    """
    Define o ícone da janela sem interromper o programa
    caso o arquivo não exista ou o sistema não suporte .ico.
    """

    try:
        janela.iconbitmap(str(caminho_asset("ultra_recibos.ico")))
    except Exception:
        pass


def centralizar(janela, largura, altura, pai=None):
    """
    Posiciona a janela no centro da janela-pai (ou da tela),
    sem ultrapassar a área visível.
    """

    janela.update_idletasks()

    escala = janela._get_window_scaling() if hasattr(janela, "_get_window_scaling") else 1.0

    tela_l = janela.winfo_screenwidth()
    tela_a = janela.winfo_screenheight()

    # Em telas pequenas (ex.: 1366x768 com zoom de 125%),
    # reduz a janela para caber na área visível.
    largura = min(largura, int((tela_l - 20) / escala))
    altura = min(altura, int((tela_a - 80) / escala))

    largura_real = int(largura * escala)
    altura_real = int(altura * escala)

    if pai is not None and pai.winfo_ismapped():
        x = pai.winfo_rootx() + (pai.winfo_width() - largura_real) // 2
        y = pai.winfo_rooty() + (pai.winfo_height() - altura_real) // 2
    else:
        x = (tela_l - largura_real) // 2
        y = (tela_a - altura_real) // 3

    x = max(0, min(x, tela_l - largura_real))
    y = max(0, min(y, tela_a - altura_real - 40))

    janela.geometry(f"{largura}x{altura}+{x}+{y}")


def trazer_para_frente(janela):
    """
    Contorna o comportamento do CTkToplevel no Windows,
    que às vezes abre a janela atrás da principal.
    """

    def _elevar():
        try:
            janela.deiconify()
            janela.lift()
            janela.focus_force()
        except Exception:
            pass

    janela.after(120, _elevar)


def abrir_arquivo(caminho):
    """
    Abre um arquivo ou pasta com o programa padrão do sistema.
    """

    caminho = str(caminho)

    if sys.platform.startswith("win"):
        os.startfile(caminho)  # noqa: S606 - comportamento desejado
    elif sys.platform == "darwin":
        subprocess.Popen(["open", caminho])
    else:
        subprocess.Popen(["xdg-open", caminho])


# =========================================
# COMPONENTES
# =========================================

def botao(pai, texto, comando, estilo="principal", **opcoes):

    estilos = {
        "principal": (COR_PRINCIPAL, COR_PRINCIPAL_HOVER, COR_TEXTO_ESCURO),
        "destaque": (COR_LARANJA, COR_LARANJA_HOVER, COR_TEXTO_ESCURO),
        "roxo": (COR_ROXO, COR_ROXO_HOVER, "#FFFFFF"),
        "neutro": (COR_NEUTRO, COR_NEUTRO_HOVER, COR_TEXTO),
        "perigo": (COR_ERRO, "#C23A3F", "#FFFFFF"),
    }

    cor, hover, cor_texto = estilos[estilo]

    parametros = dict(
        text=texto,
        command=comando,
        font=FONTE_BOTAO,
        height=38,
        corner_radius=8,
        fg_color=cor,
        hover_color=hover,
        text_color=cor_texto
    )
    parametros.update(opcoes)

    return ctk.CTkButton(pai, **parametros)


def entrada(pai, placeholder="", **opcoes):

    parametros = dict(
        placeholder_text=placeholder,
        height=38,
        font=FONTE_CAMPO,
        fg_color=COR_CAMPOS,
        text_color=COR_TEXTO,
        placeholder_text_color=COR_DISCRETO,
        border_color=COR_BORDA,
        border_width=1,
        corner_radius=7
    )
    parametros.update(opcoes)

    campo = ctk.CTkEntry(pai, **parametros)
    destacar_foco(campo)

    return campo


def destacar_foco(campo):
    """
    Borda colorida no campo com foco (facilita saber onde se
    está digitando). Campos marcados com erro mantêm o vermelho.
    """

    def ao_entrar(_evento=None):
        if not getattr(campo, "_com_erro", False):
            campo.configure(border_color=COR_PRINCIPAL, border_width=2)

    def ao_sair(_evento=None):
        if not getattr(campo, "_com_erro", False):
            campo.configure(border_color=COR_BORDA, border_width=1)

    campo.bind("<FocusIn>", ao_entrar, add="+")
    campo.bind("<FocusOut>", ao_sair, add="+")


def menu_opcoes(pai, opcoes, **parametros_extras):

    parametros = dict(
        values=opcoes,
        height=38,
        font=FONTE_CAMPO,
        dropdown_font=FONTE_CAMPO,
        fg_color=COR_CAMPOS,
        button_color=COR_PRINCIPAL,
        button_hover_color=COR_PRINCIPAL_HOVER,
        text_color=COR_TEXTO,
        dropdown_fg_color=COR_PAINEL_CLARO,
        dropdown_hover_color=COR_PRINCIPAL_HOVER,
        dropdown_text_color=COR_TEXTO,
        corner_radius=7,
        dynamic_resizing=False
    )
    parametros.update(parametros_extras)

    return ctk.CTkOptionMenu(pai, **parametros)


def rotulo(pai, texto, obrigatorio=False, **opcoes):

    parametros = dict(
        text=f"{texto} *" if obrigatorio else texto,
        font=FONTE_ROTULO,
        text_color=COR_SECUNDARIO,
        anchor="w"
    )
    parametros.update(opcoes)

    return ctk.CTkLabel(pai, **parametros)


def cartao(pai, titulo=None, cor_destaque=COR_PRINCIPAL):
    """
    Painel com cantos arredondados e título opcional.
    Retorna (cartao, area_conteudo).
    """

    quadro = ctk.CTkFrame(pai, fg_color=COR_PAINEL, corner_radius=12)

    if titulo:
        cabecalho = ctk.CTkFrame(quadro, fg_color="transparent")
        cabecalho.pack(fill="x", padx=18, pady=(14, 4))

        ctk.CTkFrame(
            cabecalho,
            width=4,
            height=18,
            corner_radius=2,
            fg_color=cor_destaque
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            cabecalho,
            text=titulo,
            font=FONTE_SECAO,
            text_color=COR_TEXTO
        ).pack(side="left")

    conteudo = ctk.CTkFrame(quadro, fg_color="transparent")
    conteudo.pack(fill="both", expand=True, padx=18, pady=(4, 14))

    return quadro, conteudo
