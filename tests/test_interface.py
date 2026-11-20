
"""
Teste da interface (requer tela; no Linux use xvfb-run).
Caixas de mensagem e abertura de PDF são simuladas.
"""

import unittest
from datetime import date
from unittest import mock

from tests import ambiente


def _tem_tela():
    try:
        import tkinter
        raiz = tkinter.Tk()
        raiz.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(_tem_tela(), "Sem ambiente gráfico disponível")
class TestInterface(unittest.TestCase):

    def setUp(self):
        ambiente.reiniciar_dados()

        self.mensagens = []
        alvo = "tkinter.messagebox"

        def registrar(tipo):
            def _f(titulo, mensagem, **_k):
                self.mensagens.append((tipo, titulo, mensagem))
                return True
            return _f

        self.patches = [
            mock.patch(f"{alvo}.showinfo", registrar("info")),
            mock.patch(f"{alvo}.showwarning", registrar("aviso")),
            mock.patch(f"{alvo}.showerror", registrar("erro")),
            mock.patch(f"{alvo}.askyesno", registrar("pergunta")),
            mock.patch("dialogos.mostrar_resumo", return_value=True),
            mock.patch("tema.abrir_arquivo"),
        ]
        for p in self.patches:
            p.start()

        import main
        self.app = main.AplicativoRecibos()
        self.app.janela.update()

    def tearDown(self):
        try:
            self.app.janela.update()
            self.app.janela.destroy()
        except Exception:
            pass
        for p in self.patches:
            p.stop()

    def preencher(self, pagamento="Crédito", autenticacao="00A12"):
        app = self.app
        app.limpar_formulario()
        app.campo_nome.insert(0, "Cliente   Ficticio Interface")
        app.campo_cpf.insert(0, "529.982.247-25")
        app.campo_codigo.insert(0, "000777")
        app.campo_valor.insert(0, "1.250,5")
        app.menu_plano.set("Gold")
        app.menu_pagamento.set(pagamento)
        app._ao_mudar_pagamento()
        app.variavel_autenticacao.set(autenticacao)
        app.menu_consultor.set(app.menu_consultor.cget("values")[1])
        app.janela.update()

    def test_fluxo_completo_salvar(self):
        import database
        import tema

        # Manutenção inicial (backup + limpeza)
        self.app._manutencao_inicial()
        self.assertEqual([m for m in self.mensagens if m[0] != "info"], [])

        self.preencher()
        self.app.salvar_recibo()

        recibos = database.listar_recibos_recentes()
        self.assertEqual(len(recibos), 1)
        r = recibos[0]
        self.assertEqual(r["nome"], "Cliente Ficticio Interface")
        self.assertEqual(r["cpf"], "52998224725")
        self.assertEqual(r["codigo_aluno"], "000777")
        self.assertEqual(r["valor_centavos"], 125050)
        self.assertEqual(r["codigo_autenticacao"], "00A12")
        self.assertEqual(r["data_pagamento"], date.today().isoformat())

        tema.abrir_arquivo.assert_called_once()
        self.assertTrue(any(m[1] == "Recibo gerado" for m in self.mensagens))

        # Formulário limpo após salvar
        self.assertEqual(self.app.campo_nome.get(), "")
        self.assertEqual(self.app.campo_data.get(), date.today().strftime("%d/%m/%Y"))
        self.assertIn("REC-000001", self.app.status_mensagem.cget("text"))

    def test_autenticacao_obrigatoria_e_filtrada(self):
        import database

        self.preencher(autenticacao="1")
        self.app.salvar_recibo()
        self.assertEqual(database.listar_recibos_recentes(), [])
        self.assertEqual(self.mensagens[-1][1], "Autenticação inválida")
        self.assertTrue(self.app.campo_autenticacao._com_erro)

        # Filtro: remove símbolos e limita a 10 caracteres
        self.app.variavel_autenticacao.set("ab-12_34567890")
        self.assertEqual(self.app.variavel_autenticacao.get(), "ab12345678")

        # PIX não exige autenticação e grava vazio
        self.preencher(pagamento="PIX CNPJ", autenticacao="")
        self.assertFalse(self.app.campo_autenticacao.winfo_ismapped())
        self.app.salvar_recibo()
        self.assertEqual(database.listar_recibos_recentes()[0]["codigo_autenticacao"], "")

    def test_validacoes_apontam_campo(self):
        self.app.limpar_formulario()
        self.app.salvar_recibo()
        self.assertEqual(self.mensagens[-1][1], "Campo obrigatório")
        self.assertTrue(self.app.campo_nome._com_erro)

        self.preencher()
        self.app.campo_cpf.delete(0, "end")
        self.app.campo_cpf.insert(0, "111.111.111-11")
        self.app.salvar_recibo()
        self.assertEqual(self.mensagens[-1][1], "CPF inválido")

        self.preencher()
        self.app.menu_consultor.set("Selecione o consultor")
        self.app.salvar_recibo()
        self.assertEqual(self.mensagens[-1][1], "Consultor obrigatório")

    def test_mascaras(self):
        app = self.app
        app.campo_cpf.delete(0, "end")
        app.campo_cpf.insert(0, "52998224725")
        app._aplicar_mascara(app.campo_cpf, __import__("validacoes").mascarar_cpf)
        self.assertEqual(app.campo_cpf.get(), "529.982.247-25")

        app.campo_valor.delete(0, "end")
        app.campo_valor.insert(0, "9,9")
        app._normalizar_valor()
        self.assertEqual(app.campo_valor.get(), "9,90")

    def test_alerta_duplicidade_nao_bloqueia(self):
        import database
        import dialogos

        self.preencher()
        self.app.salvar_recibo()
        self.preencher()
        self.app.salvar_recibo()

        # Segundo lançamento recebeu o alerta, mas foi salvo
        alerta = dialogos.mostrar_resumo.call_args.kwargs["alerta"]
        self.assertIn("REC-000001", alerta)
        self.assertEqual(len(database.listar_recibos_recentes()), 2)

    def test_opcao_nova_aparece_no_formulario(self):
        import opcoes
        opcoes.adicionar_opcao("pagamento", "Link Teste", exige_autenticacao=True)
        self.app.atualizar_opcoes_formulario()
        self.assertIn("Link Teste", self.app.menu_pagamento.cget("values"))
        self.app.menu_pagamento.set("Link Teste")
        self.app._ao_mudar_pagamento()
        self.app.janela.update()
        self.assertTrue(self.app.campo_autenticacao.winfo_ismapped())

    def test_troca_de_aparencia(self):
        import customtkinter as ctk
        import tema
        tema.aplicar_tema("claro")
        self.app.janela.update()
        self.assertEqual(ctk.get_appearance_mode(), "Light")
        tema.aplicar_tema("escuro")
        self.app.janela.update()
        self.assertEqual(ctk.get_appearance_mode(), "Dark")

    def test_janelas_auxiliares(self):
        import database

        self.preencher()
        self.app.salvar_recibo()

        self.app.abrir_historico()
        self.app.janela.update()
        self.assertTrue(self.app.tela_historico.winfo_exists())

        # Reabrir não cria outra janela
        anterior = self.app.tela_historico
        self.app.abrir_historico()
        self.assertIs(anterior, self.app.tela_historico)

        from tela_historico import reimprimir_recibo
        reimprimir_recibo(database.listar_recibos_recentes()[0]["id"])

        self.app.abrir_configuracoes()
        self.app.janela.update()
        self.assertTrue(self.app.tela_configuracoes.winfo_exists())
        self.assertEqual([m for m in self.mensagens if m[0] == "erro"], [])


if __name__ == "__main__":
    unittest.main()
