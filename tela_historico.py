
"""
Histórico de recibos (últimos 90 dias) e reimpressão.

A reimpressão NÃO cria um novo registro: o PDF é gerado
novamente a partir dos dados gravados no banco (empresa,
logotipo e valores da data de emissão).
"""

import re

from datetime import date, datetime
from tkinter import messagebox

import customtkinter as ctk

import tema as t

from configuracoes import DIAS_RETENCAO, HORAS_HISTORICO_INICIAL
from registro import obter_logger
from validacoes import formatar_reais, formatar_cpf


log = obter_logger("historico")


# =========================================
# REIMPRESSÃO
# =========================================

def reimprimir_recibo(id_recibo, pai=None):

    from receipt_pdf import criar_pdf, PdfEmUsoError
    from caminhos import PASTA_PDFS

    try:
        caminho_pdf = criar_pdf(id_recibo)

    except PdfEmUsoError:
        # O PDF já existe e está aberto (ex.: no leitor de PDF):
        # basta trazê-lo novamente.
        caminho_pdf = PASTA_PDFS / f"REC-{id_recibo:06d}.pdf"

        if not caminho_pdf.is_file():
            raise

    except Exception as erro:
        log.exception("Falha na reimpressão de %s", id_recibo)
        messagebox.showerror(
            "Erro na reimpressão",
            f"Não foi possível gerar o recibo:\n{erro}",
            parent=pai
        )
        return

    if caminho_pdf is None:
        messagebox.showerror(
            "Recibo não encontrado",
            "Este recibo não foi localizado no banco.",
            parent=pai
        )
        return

    try:
        t.abrir_arquivo(caminho_pdf)
    except OSError as erro:
        messagebox.showerror(
            "Erro na reimpressão",
            f"Não foi possível abrir o recibo:\n{erro}\n\nLocal: {caminho_pdf}",
            parent=pai
        )


# =========================================
# JANELA DE HISTÓRICO
# =========================================

def abrir_historico(janela):

    from database import pesquisar_recibos, listar_recibos_recentes

    historico = ctk.CTkToplevel(janela)
    historico.title("Histórico de Recibos")
    historico.configure(fg_color=t.COR_FUNDO)
    historico.minsize(760, 460)
    t.aplicar_icone(historico)
    t.centralizar(historico, 940, 600, janela)

    # ---------------------------------
    # CABEÇALHO E PESQUISA
    # ---------------------------------

    topo = ctk.CTkFrame(historico, fg_color="transparent")
    topo.pack(fill="x", padx=24, pady=(18, 6))

    ctk.CTkLabel(
        topo,
        text="Histórico de recibos",
        font=t.fonte(22, True),
        text_color=t.COR_TEXTO
    ).pack(side="left")

    contador = ctk.CTkLabel(
        topo,
        text="",
        font=t.FONTE_PEQUENA,
        text_color=t.COR_SECUNDARIO
    )
    contador.pack(side="right")

    barra_busca = ctk.CTkFrame(historico, fg_color="transparent")
    barra_busca.pack(fill="x", padx=24, pady=(4, 8))

    campo_busca = t.entrada(
        barra_busca,
        "Pesquisar por nome, CPF ou código do aluno",
        height=42
    )
    campo_busca.pack(side="left", fill="x", expand=True)

    def limpar_busca():
        campo_busca.delete(0, "end")
        carregar()
        campo_busca.focus_set()

    t.botao(barra_busca, "Limpar", limpar_busca, estilo="neutro", width=90, height=42).pack(
        side="left", padx=(8, 0)
    )

    ctk.CTkLabel(
        historico,
        text=(
            f"Mostrando os recibos das últimas {HORAS_HISTORICO_INICIAL} horas. "
            f"A pesquisa procura nos últimos {DIAS_RETENCAO} dias. "
            "\"Abrir PDF\" gera novamente o documento com os dados originais."
        ),
        font=t.FONTE_PEQUENA,
        text_color=t.COR_DISCRETO,
        anchor="w"
    ).pack(fill="x", padx=26)

    lista = ctk.CTkScrollableFrame(historico, fg_color=t.COR_PAINEL, corner_radius=12)
    lista.pack(fill="both", expand=True, padx=24, pady=(6, 18))

    # ---------------------------------
    # LISTAGEM
    # ---------------------------------

    def criar_linha(recibo):

        id_recibo = recibo["id"]
        numero = f"REC-{id_recibo:06d}"

        try:
            data_pg = date.fromisoformat(recibo["data_pagamento"]).strftime("%d/%m/%Y")
        except (TypeError, ValueError):
            data_pg = str(recibo["data_pagamento"])

        try:
            emitido = datetime.fromisoformat(recibo["emitido_em"]).strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            emitido = str(recibo["emitido_em"])

        forma = recibo["forma_pagamento"]

        if recibo["codigo_autenticacao"]:
            forma += f" (Aut. {recibo['codigo_autenticacao']})"

        linha = ctk.CTkFrame(lista, fg_color=t.COR_CAMPOS, corner_radius=10)
        linha.pack(fill="x", padx=6, pady=4)
        linha.grid_columnconfigure(0, weight=1)

        info = ctk.CTkFrame(linha, fg_color="transparent")
        info.grid(row=0, column=0, sticky="ew", padx=14, pady=8)

        ctk.CTkLabel(
            info,
            text=f"{numero}  ·  {recibo['nome']}",
            font=t.fonte(13, True),
            text_color=t.COR_TEXTO,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            info,
            text=(
                f"CPF {formatar_cpf(recibo['cpf'])}   ·   "
                f"Código {recibo['codigo_aluno']}   ·   "
                f"Consultor: {recibo['consultor']}"
            ),
            font=t.FONTE_PEQUENA,
            text_color=t.COR_SECUNDARIO,
            anchor="w"
        ).pack(fill="x")

        ctk.CTkLabel(
            info,
            text=(
                f"{recibo['plano']}   ·   {formatar_reais(recibo['valor_centavos'])}   ·   "
                f"{forma}   ·   Pago em {data_pg}   ·   Emitido em {emitido}"
            ),
            font=t.FONTE_PEQUENA,
            text_color=t.COR_SECUNDARIO,
            anchor="w"
        ).pack(fill="x")

        t.botao(
            linha,
            "Abrir PDF",
            lambda id_atual=id_recibo: reimprimir_recibo(id_atual, historico),
            estilo="roxo",
            width=120,
            height=36
        ).grid(row=0, column=1, padx=14, pady=8)

    def mostrar_aviso(texto):
        ctk.CTkLabel(
            lista,
            text=texto,
            font=t.fonte(13),
            text_color=t.COR_SECUNDARIO
        ).pack(pady=30)

    def carregar():

        for componente in lista.winfo_children():
            componente.destroy()

        termo = campo_busca.get().strip()

        try:
            if termo:
                registros = pesquisar_recibos(termo)

                # Tenta também o CPF sem pontuação
                cpf_busca = re.sub(r"\D", "", termo)

                if not registros and len(cpf_busca) >= 3 and cpf_busca != termo:
                    registros = pesquisar_recibos(cpf_busca)
            else:
                registros = listar_recibos_recentes()

        except Exception as erro:
            log.exception("Erro na pesquisa do histórico")
            messagebox.showerror(
                "Erro de pesquisa",
                f"Não foi possível consultar os recibos:\n{erro}",
                parent=historico
            )
            return

        if termo:
            contador.configure(text=f"{len(registros)} resultado(s)" + (" — mostrando os 50 mais recentes" if len(registros) >= 50 else ""))
        else:
            contador.configure(
                text=f"{len(registros)} recibo(s) nas últimas {HORAS_HISTORICO_INICIAL} horas"
            )

        if not registros:
            mostrar_aviso(
                "Nenhum recibo encontrado."
                if termo else
                f"Nenhum recibo nas últimas {HORAS_HISTORICO_INICIAL} horas.\n"
                f"Use a pesquisa para procurar nos últimos {DIAS_RETENCAO} dias."
            )
            return

        for recibo in registros:
            criar_linha(recibo)

        # Volta a lista para o topo
        try:
            lista._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    # Pesquisa automática enquanto digita (com pequena espera)
    agendamento = {"id": None}

    def agendar_busca(_evento=None):
        if agendamento["id"] is not None:
            historico.after_cancel(agendamento["id"])
        agendamento["id"] = historico.after(350, carregar)

    campo_busca.bind("<KeyRelease>", agendar_busca)
    campo_busca.bind("<Return>", lambda e: carregar())
    historico.bind("<Escape>", lambda e: historico.destroy())

    carregar()
    campo_busca.focus_set()
    t.trazer_para_frente(historico)

    return historico
