
import json
import os
import sqlite3
import unittest
from contextlib import closing
from datetime import datetime, timedelta

from PIL import Image

from tests import ambiente

import caminhos
import database
import backup
import limpeza_pdfs
import empresa_config
import consultores
import configuracoes
import receipt_pdf


def texto_pdf(caminho):
    from pypdf import PdfReader
    return PdfReader(str(caminho)).pages[0].extract_text()


class BaseTeste(unittest.TestCase):

    def setUp(self):
        ambiente.reiniciar_dados()
        database.criar_banco()
        consultores.inicializar_consultores()


class TestRecibos(BaseTeste):

    def test_insercao_preserva_textos(self):
        id_recibo = database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        recibo = database.buscar_recibo_por_id(id_recibo)

        self.assertEqual(recibo["codigo_aluno"], "000123")       # zeros à esquerda
        self.assertEqual(recibo["codigo_autenticacao"], "00A12")  # zeros à esquerda
        self.assertEqual(recibo["valor_centavos"], 12990)
        self.assertEqual(recibo["consultor"], "Consultor Teste")
        # Empresa padrão gravada no recibo
        self.assertEqual(recibo["emissor_razao_social"], configuracoes.RAZAO_SOCIAL)
        self.assertEqual(recibo["emissor_cnpj"], configuracoes.CNPJ_EMPRESA)
        self.assertIsNone(recibo["logo_imagem"])

    def test_empresa_e_logo_historicos(self):
        # Recibo 1 com a empresa padrão
        id1 = database.inserir_recibo(**ambiente.RECIBO_FICTICIO)

        # Nova empresa + logotipo
        empresa_config.salvar_empresa("Empresa Ficticia Ltda", "12.ABC.345/01DE-35", "Sobradinho")
        imagem = ambiente.PASTA / "logo_origem.png"
        Image.new("RGBA", (3000, 1500), (47, 171, 171, 255)).save(imagem)
        empresa_config.salvar_logo_empresa(imagem)

        with Image.open(empresa_config.ARQUIVO_LOGO) as logo:
            self.assertLessEqual(max(logo.size), empresa_config.LOGO_DIMENSAO_MAXIMA)

        id2 = database.inserir_recibo(**ambiente.RECIBO_FICTICIO)

        r1 = database.buscar_recibo_por_id(id1)
        r2 = database.buscar_recibo_por_id(id2)

        self.assertEqual(r1["emissor_razao_social"], configuracoes.RAZAO_SOCIAL)
        self.assertIsNone(r1["logo_imagem"])
        self.assertEqual(r2["emissor_razao_social"], "Empresa Ficticia Ltda")
        self.assertEqual(r2["emissor_cnpj"], "12ABC34501DE35")
        self.assertTrue(r2["logo_imagem"])
        self.assertIsNone(r2["emissor_logo"])  # 2.3.0: guardado em "logos"

        # Vários recibos com o mesmo logo = uma única imagem gravada
        database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        with database.conectar() as conexao:
            self.assertEqual(conexao.execute("SELECT COUNT(*) FROM logos").fetchone()[0], 1)

        # PDFs refletem cada empresa
        t1 = texto_pdf(receipt_pdf.criar_pdf(id1))
        t2 = texto_pdf(receipt_pdf.criar_pdf(id2))
        self.assertIn(configuracoes.CNPJ_EMPRESA, t1)
        self.assertIn(configuracoes.RAZAO_SOCIAL, t1)
        self.assertIn("12.ABC.345/01DE-35", t2)
        self.assertIn("Empresa Ficticia Ltda", t2)

    def test_cnpj_invalido_rejeitado(self):
        with self.assertRaises(ValueError):
            empresa_config.salvar_empresa("X Ltda", "11.222.333/0001-82", "Brasília")

    def test_empresa_json_danificado(self):
        empresa_config.ARQUIVO_EMPRESA.write_text("{corrompido", encoding="utf-8")
        with self.assertRaises(ValueError) as contexto:
            empresa_config.carregar_empresa()
        self.assertIn("danificado", str(contexto.exception))

    def test_pdf_conteudo(self):
        id_recibo = database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        caminho = receipt_pdf.criar_pdf(id_recibo)
        self.assertEqual(caminho.name, f"REC-{id_recibo:06d}.pdf")
        texto = texto_pdf(caminho)
        for esperado in ("RECIBO PROVISÓRIO", "CLIENTE FICTICIO UM", "CPF: 529.982.247-25",
                         "000123", "00A12", "C. CRÉDITO", "R$129,90", "10/11/2026",
                         "Consultor Teste", "Gold Pro"):
            self.assertIn(esperado, texto, esperado)
        # Nenhum arquivo temporário deixado para trás
        self.assertEqual(list(caminhos.PASTA_PDFS.glob("*.tmp")), [])

    def test_pdf_sem_autenticacao_mostra_hifen(self):
        dados = dict(ambiente.RECIBO_FICTICIO, forma_pagamento="PIX CNPJ", codigo_autenticacao="")
        texto = texto_pdf(receipt_pdf.criar_pdf(database.inserir_recibo(**dados)))
        self.assertIn("PIXCNPJ", texto)

    def test_reimpressao_nao_cria_registro(self):
        id_recibo = database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        receipt_pdf.criar_pdf(id_recibo)
        receipt_pdf.criar_pdf(id_recibo)
        with database.conectar() as conexao:
            total, = conexao.execute("SELECT COUNT(*) FROM recibos").fetchone()
        self.assertEqual(total, 1)

    def test_pdf_recibo_inexistente(self):
        self.assertIsNone(receipt_pdf.criar_pdf(9999))


class TestPesquisa(BaseTeste):

    def test_pesquisa_e_periodo(self):
        id_novo = database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        id_antigo = database.inserir_recibo(**dict(ambiente.RECIBO_FICTICIO, nome="Cliente Antigo"))

        antigo = (datetime.now() - timedelta(days=91)).isoformat(timespec="seconds")
        with database.conectar() as conexao:
            conexao.execute("UPDATE recibos SET emitido_em = ? WHERE id = ?", (antigo, id_antigo))

        ids = [r["id"] for r in database.pesquisar_recibos("Cliente")]
        self.assertEqual(ids, [id_novo])
        self.assertEqual([r["id"] for r in database.pesquisar_recibos("529982")], [id_novo])
        self.assertEqual([r["id"] for r in database.pesquisar_recibos("000123")], [id_novo])
        self.assertEqual([r["id"] for r in database.listar_recibos_recentes()], [id_novo])

    def test_lista_inicial_48h_pesquisa_90_dias(self):
        def com_idade(nome, horas):
            id_recibo = database.inserir_recibo(**dict(ambiente.RECIBO_FICTICIO, nome=nome))
            emitido = (datetime.now() - timedelta(hours=horas)).isoformat(timespec="seconds")
            with database.conectar() as conexao:
                conexao.execute("UPDATE recibos SET emitido_em = ? WHERE id = ?", (emitido, id_recibo))
            return id_recibo

        id_ontem = com_idade("Aluno Ontem", 30)
        id_3_dias = com_idade("Aluno Tres Dias", 72)
        id_80_dias = com_idade("Aluno Oitenta Dias", 80 * 24)
        id_100_dias = com_idade("Aluno Cem Dias", 100 * 24)

        # Ao abrir: somente as últimas 48 horas
        self.assertEqual([r["id"] for r in database.listar_recibos_recentes()], [id_ontem])
        # Pesquisando: até 90 dias
        self.assertEqual([r["id"] for r in database.pesquisar_recibos("Tres Dias")], [id_3_dias])
        self.assertEqual([r["id"] for r in database.pesquisar_recibos("Oitenta")], [id_80_dias])
        self.assertEqual(database.pesquisar_recibos("Cem Dias"), [])
        self.assertIsNotNone(database.buscar_recibo_por_id(id_100_dias))  # registro preservado
        self.assertEqual(database.pesquisar_recibos("   "), [])

    def test_curingas_sao_literais(self):
        database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        self.assertEqual(database.pesquisar_recibos("%"), [])
        self.assertEqual(database.pesquisar_recibos("_"), [])

    def test_estatisticas(self):
        database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        estat = database.estatisticas_banco()
        self.assertEqual(estat["total_recibos"], 1)
        self.assertEqual(estat["recibos_periodo"], 1)


class TestConsultores(BaseTeste):

    def test_iniciais_e_duplicidade(self):
        nomes = [n for _, n, _ in consultores.listar_consultores()]
        self.assertEqual(len(nomes), len(consultores.CONSULTORES_INICIAIS))
        consultores.cadastrar_consultor("  Novo   Consultor  ")
        self.assertIn("Novo Consultor", [n for _, n, _ in consultores.listar_consultores()])
        with self.assertRaises(ValueError):
            consultores.cadastrar_consultor("novo consultor")  # NOCASE
        with self.assertRaises(ValueError):
            consultores.cadastrar_consultor("ab")

    def test_desativar(self):
        id_c, nome, _ = consultores.listar_consultores()[0]
        consultores.alterar_status_consultor(id_c, False)
        self.assertNotIn(nome, [n for _, n, _ in consultores.listar_consultores()])
        self.assertIn(nome, [n for _, n, _ in consultores.listar_consultores(apenas_ativos=False)])


class TestBackup(BaseTeste):

    def test_backup_consistente_e_configuracao(self):
        database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        empresa_config.salvar_empresa("Empresa Ficticia Ltda", "11222333000181", "Brasília")

        destino = backup.criar_backup()
        self.assertIsNotNone(destino)
        self.assertTrue(destino.is_file())

        with closing(sqlite3.connect(destino)) as conexao:
            self.assertEqual(conexao.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(conexao.execute("SELECT COUNT(*) FROM recibos").fetchone()[0], 1)

        pasta_config = caminhos.PASTA_BACKUPS / f"configuracao_{destino.stem[-8:]}"
        self.assertTrue((pasta_config / "empresa.json").is_file())
        self.assertEqual(json.loads((pasta_config / "empresa.json").read_text("utf-8"))["cidade"], "Brasília")

        self.assertEqual(backup.ultimo_backup()[0], destino)
        self.assertEqual(list(caminhos.PASTA_BACKUPS.glob("backup_temp_*")), [])

    def test_backup_sem_banco(self):
        caminhos.CAMINHO_BANCO.unlink()
        self.assertIsNone(backup.criar_backup())


class TestLimpeza(BaseTeste):

    def _criar_pdf_com_idade(self, dias):
        id_recibo = database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        emitido = (datetime.now() - timedelta(days=dias)).isoformat(timespec="seconds")
        with database.conectar() as conexao:
            conexao.execute("UPDATE recibos SET emitido_em = ? WHERE id = ?", (emitido, id_recibo))
        return id_recibo, receipt_pdf.criar_pdf(id_recibo)

    def test_retencao_90_dias(self):
        _, pdf_novo = self._criar_pdf_com_idade(10)
        _, pdf_limite = self._criar_pdf_com_idade(89)
        id_velho, pdf_velho = self._criar_pdf_com_idade(95)

        # PDFs que não devem ser tocados
        orfao = caminhos.PASTA_PDFS / "REC-999999.pdf"
        orfao.write_bytes(b"%PDF-teste")
        outro = caminhos.PASTA_PDFS / "documento.pdf"
        outro.write_bytes(b"%PDF-teste")

        resumo = limpeza_pdfs.limpar_pdfs_antigos(simular=True)
        self.assertEqual(resumo["antigos"], 1)
        self.assertTrue(pdf_velho.exists())

        resumo = limpeza_pdfs.limpar_pdfs_antigos(simular=False)
        self.assertEqual(resumo["excluidos"], 1)
        self.assertFalse(pdf_velho.exists())
        for arquivo in (pdf_novo, pdf_limite, orfao, outro):
            self.assertTrue(arquivo.exists(), arquivo.name)

        # O registro continua no banco e o PDF pode ser gerado de novo
        self.assertIsNotNone(database.buscar_recibo_por_id(id_velho))
        self.assertTrue(receipt_pdf.criar_pdf(id_velho).exists())


class TestNovidades230(BaseTeste):

    def test_indice_historico(self):
        with database.conectar() as conexao:
            indices = {i[1] for i in conexao.execute("PRAGMA index_list(recibos)")}
        self.assertIn("idx_recibos_emitido_em", indices)

    def test_migracao_logos_2_2_0(self):
        # Simula banco da 2.2.0: logo repetido em cada recibo
        logo_a = (ambiente.PASTA / "a.png")
        Image.new("RGBA", (300, 100), (239, 129, 40, 255)).save(logo_a)
        logo_b = (ambiente.PASTA / "b.png")
        Image.new("RGBA", (300, 100), (170, 72, 148, 255)).save(logo_b)
        bytes_a, bytes_b = logo_a.read_bytes(), logo_b.read_bytes()

        ids = [database.inserir_recibo(**ambiente.RECIBO_FICTICIO) for _ in range(4)]
        with database.conectar() as conexao:
            for i, id_recibo in enumerate(ids):
                conexao.execute(
                    "UPDATE recibos SET emissor_logo = ?, emissor_logo_hash = NULL WHERE id = ?",
                    (bytes_a if i < 3 else bytes_b, id_recibo))
            conexao.execute("DELETE FROM logos")

        self.assertEqual(database.migrar_logos(), 4)
        self.assertEqual(database.migrar_logos(), 0)  # idempotente

        with database.conectar() as conexao:
            self.assertEqual(conexao.execute("SELECT COUNT(*) FROM logos").fetchone()[0], 2)
            self.assertEqual(conexao.execute(
                "SELECT COUNT(*) FROM recibos WHERE emissor_logo IS NOT NULL").fetchone()[0], 0)

        # Cada recibo devolve exatamente a imagem original
        for i, id_recibo in enumerate(ids):
            esperado = bytes_a if i < 3 else bytes_b
            self.assertEqual(bytes(database.buscar_recibo_por_id(id_recibo)["logo_imagem"]), esperado)
            self.assertTrue(receipt_pdf.criar_pdf(id_recibo).exists())

        # Cópia de segurança feita antes da migração
        self.assertEqual(len(list(caminhos.PASTA_BACKUPS.glob("antes_migracao_logos_*.db"))), 1)

    def test_duplicidade_apenas_avisa(self):
        dados = ambiente.RECIBO_FICTICIO
        self.assertEqual(database.buscar_duplicados(dados["cpf"], dados["valor_centavos"], dados["data_pagamento"]), [])
        id1 = database.inserir_recibo(**dados)
        iguais = database.buscar_duplicados(dados["cpf"], dados["valor_centavos"], dados["data_pagamento"])
        self.assertEqual([r["id"] for r in iguais], [id1])
        # Lançar de novo continua permitido
        self.assertGreater(database.inserir_recibo(**dados), id1)
        self.assertEqual(database.buscar_duplicados(dados["cpf"], 1, dados["data_pagamento"]), [])

    def test_opcoes_editaveis(self):
        import opcoes
        opcoes.inicializar_opcoes()
        opcoes.inicializar_opcoes()  # não duplica

        from configuracoes import PLANOS, FORMAS_PAGAMENTO
        self.assertEqual(opcoes.nomes_ativos("plano"), PLANOS)
        self.assertEqual(opcoes.nomes_ativos("pagamento"), FORMAS_PAGAMENTO)
        self.assertEqual(opcoes.pagamentos_com_autenticacao(), {"Crédito", "Débito", "DIN + MAQ"})

        opcoes.adicionar_opcao("plano", "  Plano   Teste ")
        self.assertEqual(opcoes.nomes_ativos("plano")[-1], "Plano Teste")
        with self.assertRaises(ValueError):
            opcoes.adicionar_opcao("plano", "plano teste")

        opcoes.adicionar_opcao("pagamento", "Link de pagamento", exige_autenticacao=True)
        self.assertIn("Link de pagamento", opcoes.pagamentos_com_autenticacao())

        id_diaria = [i for i, n, *_ in opcoes.listar_opcoes("plano") if n == "Diária"][0]
        opcoes.alterar_status_opcao(id_diaria, False)
        self.assertNotIn("Diária", opcoes.nomes_ativos("plano"))
        opcoes.alterar_status_opcao(id_diaria, True)

        id_gold = [i for i, n, *_ in opcoes.listar_opcoes("plano") if n == "Gold"][0]
        opcoes.mover_opcao(id_gold, -1)
        self.assertEqual(opcoes.nomes_ativos("plano")[:2], ["Gold", "Diária"])

        # Recibo antigo mantém o nome gravado após renomear o plano
        id_recibo = database.inserir_recibo(**dict(ambiente.RECIBO_FICTICIO, plano="Gold"))
        opcoes.renomear_opcao(id_gold, "Gold Novo")
        self.assertEqual(database.buscar_recibo_por_id(id_recibo)["plano"], "Gold")

    def test_nao_desativa_ultima_opcao(self):
        import opcoes
        opcoes.inicializar_opcoes()
        ativos = opcoes.listar_opcoes("pagamento")
        for id_opcao, *_ in ativos[:-1]:
            opcoes.alterar_status_opcao(id_opcao, False)
        with self.assertRaises(ValueError):
            opcoes.alterar_status_opcao(ativos[-1][0], False)


class TestNovidades240(BaseTeste):

    def test_retencao_90_backups(self):
        from datetime import date
        caminhos.PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
        hoje = date(2026, 11, 14)
        for dias in (0, 30, 90, 91, 200):
            d = (hoje - timedelta(days=dias)).strftime("%Y%m%d")
            (caminhos.PASTA_BACKUPS / f"backup_recibos_{d}.db").write_bytes(b"x")
            (caminhos.PASTA_BACKUPS / f"configuracao_{d}").mkdir()
        protegido = caminhos.PASTA_BACKUPS / "antes_restauracao_20200101_000000.db"
        protegido.write_bytes(b"x")

        self.assertEqual(backup.aplicar_retencao(hoje=hoje), 4)  # 91 e 200 dias (db + pasta)
        restantes = sorted(p.name for p in caminhos.PASTA_BACKUPS.glob("backup_recibos_*.db"))
        self.assertEqual(len(restantes), 3)
        self.assertTrue(protegido.exists())

    def test_restauracao_completa(self):
        id1 = database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        arquivo = backup.criar_backup()
        info = backup.inspecionar_backup(arquivo, verificar_integridade=True)
        self.assertEqual((info["total_recibos"], info["ultimo_id"], info["integro"]), (1, id1, True))

        # Depois do backup: mais 2 recibos
        database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        database.inserir_recibo(**ambiente.RECIBO_FICTICIO)

        copia = backup.restaurar_backup(arquivo)
        self.assertEqual(database.estatisticas_banco()["total_recibos"], 1)
        self.assertTrue(copia.name.startswith("antes_restauracao_"))

        # A cópia guardada permite desfazer
        self.assertEqual(backup.inspecionar_backup(copia)["total_recibos"], 3)
        backup.restaurar_backup(copia)
        self.assertEqual(database.estatisticas_banco()["total_recibos"], 3)

        # O banco restaurado funciona normalmente
        self.assertTrue(receipt_pdf.criar_pdf(id1).exists())
        self.assertGreater(database.inserir_recibo(**ambiente.RECIBO_FICTICIO), 3)

    def test_restaurar_configuracao_do_dia(self):
        empresa_config.salvar_empresa("Empresa Antiga Ltda", "11222333000181", "Brasília")
        arquivo = backup.criar_backup()
        empresa_config.salvar_empresa("Empresa Nova Ltda", "11222333000181", "Brasília")
        backup.restaurar_backup(arquivo, restaurar_configuracao=True)
        self.assertEqual(empresa_config.carregar_empresa()["razao_social"], "Empresa Antiga Ltda")

    def test_arquivo_invalido_nao_restaura(self):
        database.inserir_recibo(**ambiente.RECIBO_FICTICIO)
        falso = ambiente.PASTA / "nao_e_banco.db"
        falso.write_bytes(b"isto nao e um banco")
        outro = ambiente.PASTA / "outro.db"
        with closing(sqlite3.connect(outro)) as c, c:
            c.execute("CREATE TABLE qualquer (x)")
        for arquivo in (falso, outro, ambiente.PASTA / "inexistente.db"):
            with self.assertRaises(ValueError):
                backup.restaurar_backup(arquivo)
        self.assertEqual(database.estatisticas_banco()["total_recibos"], 1)

    def test_aparencia(self):
        import tema
        import preferencias
        from datetime import datetime as dt
        self.assertEqual(preferencias.obter_preferencia("aparencia"), "auto_horario")
        self.assertEqual(tema.modo_efetivo("auto_horario", dt(2026, 11, 14, 9)), "light")
        self.assertEqual(tema.modo_efetivo("auto_horario", dt(2026, 11, 14, 19)), "dark")
        self.assertEqual(tema.modo_efetivo("auto_horario", dt(2026, 11, 14, 5)), "dark")
        self.assertEqual(tema.modo_efetivo("escuro"), "dark")
        self.assertEqual(tema.modo_efetivo("claro"), "light")
        self.assertEqual(tema.modo_efetivo("sistema"), "system")
        preferencias.salvar_preferencia("aparencia", "escuro")
        self.assertEqual(preferencias.obter_preferencia("aparencia"), "escuro")
        preferencias.ARQUIVO_PREFERENCIAS.write_text("{quebrado", encoding="utf-8")
        self.assertEqual(preferencias.obter_preferencia("aparencia"), "auto_horario")


class TestMigracaoBancoAntigo(unittest.TestCase):
    """
    Banco criado pela versão 1.x (sem colunas novas) deve ser
    migrado sem perda de dados.
    """

    def test_migracao(self):
        ambiente.reiniciar_dados()

        with closing(sqlite3.connect(caminhos.CAMINHO_BANCO)) as conexao, conexao:
            conexao.execute("""
                CREATE TABLE recibos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL, cpf TEXT NOT NULL, codigo_aluno TEXT NOT NULL,
                    plano TEXT NOT NULL, valor_centavos INTEGER NOT NULL,
                    forma_pagamento TEXT NOT NULL, data_pagamento TEXT NOT NULL,
                    consultor TEXT NOT NULL, emitido_em TEXT NOT NULL)
            """)
            conexao.execute(
                "INSERT INTO recibos (nome, cpf, codigo_aluno, plano, valor_centavos, "
                "forma_pagamento, data_pagamento, consultor, emitido_em) "
                "VALUES ('Antigo Ficticio','11144477735','007','Gold',5000,'Dinheiro',"
                "'2026-11-01','kaio',?)",
                (datetime.now().isoformat(timespec="seconds"),)
            )

        database.criar_banco()
        database.criar_banco()  # idempotente

        with database.conectar() as conexao:
            colunas = {c[1] for c in conexao.execute("PRAGMA table_info(recibos)")}

        for coluna in ("emissor_logo", "emissor_razao_social", "emissor_cnpj",
                       "emissor_cidade", "codigo_autenticacao"):
            self.assertIn(coluna, colunas)

        recibo = database.buscar_recibo_por_id(1)
        self.assertEqual(recibo["codigo_aluno"], "007")

        # Recibo antigo sem empresa gravada: mesma regra da 2.1.2
        with self.assertRaises(ValueError):
            receipt_pdf.criar_pdf(1)


class TestBancoReal212(unittest.TestCase):
    """
    Banco gerado pela versão 2.1.2 original (dados fictícios),
    quando disponível em ULTRARECIBOS_BANCO_212.
    """

    def test_compatibilidade(self):
        origem = os.environ.get("ULTRARECIBOS_BANCO_212")
        if not origem:
            self.skipTest("ULTRARECIBOS_BANCO_212 não definido")

        ambiente.reiniciar_dados()
        caminhos.CAMINHO_BANCO.write_bytes(open(origem, "rb").read())
        database.criar_banco()
        consultores.inicializar_consultores()

        recibos = database.listar_recibos_recentes()
        self.assertGreaterEqual(len(recibos), 1)
        for r in recibos:
            self.assertTrue(receipt_pdf.criar_pdf(r["id"]).exists())


if __name__ == "__main__":
    unittest.main()
