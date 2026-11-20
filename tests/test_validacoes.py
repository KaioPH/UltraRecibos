
import unittest
from datetime import date, timedelta
from decimal import Decimal

from tests import ambiente

# Garante a pasta temporária antes de importar o programa
_PASTA_TESTE = ambiente.PASTA

from validacoes import (
    validar_cpf, mascarar_cpf, formatar_cpf,
    validar_valor, valor_para_centavos, formatar_reais, normalizar_valor_digitado,
    validar_data, mascarar_data,
    filtrar_autenticacao, validar_autenticacao,
    validar_cnpj, normalizar_cnpj, formatar_cnpj,
    escapar_like,
)


class TestCPF(unittest.TestCase):

    def test_cpfs_validos(self):
        for cpf in ("52998224725", "529.982.247-25", "111.444.777-35", " 11144477735 "):
            self.assertTrue(validar_cpf(cpf), cpf)

    def test_cpfs_invalidos(self):
        for cpf in ("52998224724", "11111111111", "123", "", None, "5299822472a", "529982247251"):
            self.assertFalse(validar_cpf(cpf), cpf)

    def test_mascara(self):
        self.assertEqual(mascarar_cpf("529"), "529")
        self.assertEqual(mascarar_cpf("5299"), "529.9")
        self.assertEqual(mascarar_cpf("5299822"), "529.982.2")
        self.assertEqual(mascarar_cpf("52998224725999"), "529.982.247-25")
        self.assertEqual(formatar_cpf("52998224725"), "529.982.247-25")
        self.assertEqual(formatar_cpf("abc"), "abc")


class TestValor(unittest.TestCase):

    def test_validos(self):
        casos = {
            "9,90": Decimal("9.90"), "150": Decimal("150"), "1.250,00": Decimal("1250.00"),
            "0,01": Decimal("0.01"), "10,5": Decimal("10.5"), "1.000.000,99": Decimal("1000000.99"),
        }
        for texto, esperado in casos.items():
            self.assertEqual(validar_valor(texto), esperado, texto)

    def test_invalidos(self):
        for texto in ("0", "0,00", "-5", "10.5", "1,234", "abc", "", "1.25,00", "9,999"):
            self.assertIsNone(validar_valor(texto), texto)

    def test_centavos_exatos(self):
        self.assertEqual(valor_para_centavos(validar_valor("0,29")), 29)
        self.assertEqual(valor_para_centavos(validar_valor("1.234,56")), 123456)
        self.assertEqual(valor_para_centavos(validar_valor("19,99")), 1999)

    def test_formatacao(self):
        self.assertEqual(formatar_reais(12990), "R$ 129,90")
        self.assertEqual(formatar_reais(123456789), "R$ 1.234.567,89")
        self.assertEqual(formatar_reais(5), "R$ 0,05")
        self.assertEqual(normalizar_valor_digitado("9,9"), "9,90")
        self.assertEqual(normalizar_valor_digitado("1250"), "1.250,00")
        self.assertEqual(normalizar_valor_digitado("abc"), "abc")


class TestData(unittest.TestCase):

    def test_data(self):
        self.assertEqual(validar_data("10/11/2026"), date(2026, 11, 10))
        self.assertIsNone(validar_data("31/02/2026"))
        self.assertIsNone(validar_data("2026-11-10"))
        futura = (date.today() + timedelta(days=1)).strftime("%d/%m/%Y")
        self.assertIsNone(validar_data(futura))
        self.assertEqual(validar_data(date.today().strftime("%d/%m/%Y")), date.today())

    def test_mascara(self):
        self.assertEqual(mascarar_data("1011"), "10/11")
        self.assertEqual(mascarar_data("10112026"), "10/11/2026")
        self.assertEqual(mascarar_data("10/11/20269"), "10/11/2026")


class TestAutenticacao(unittest.TestCase):

    def test_limites_2_a_10(self):
        self.assertFalse(validar_autenticacao("A"))
        self.assertTrue(validar_autenticacao("0A"))
        self.assertTrue(validar_autenticacao("0123456789"))
        self.assertFalse(validar_autenticacao("01234567890"))
        self.assertFalse(validar_autenticacao("12-34"))
        self.assertFalse(validar_autenticacao(""))

    def test_preserva_zeros_e_caixa(self):
        self.assertEqual(filtrar_autenticacao("00a-12 b"), "00a12b")
        self.assertEqual(filtrar_autenticacao("0000000000999"), "0000000000")
        self.assertEqual(filtrar_autenticacao("ção12"), "o12")


class TestCNPJ(unittest.TestCase):

    def test_numerico(self):
        self.assertTrue(validar_cnpj("11.222.333/0001-81"))
        self.assertTrue(validar_cnpj("11222333000181"))
        self.assertFalse(validar_cnpj("11.222.333/0001-82"))
        self.assertFalse(validar_cnpj("00000000000000"))
        self.assertFalse(validar_cnpj("123"))

    def test_alfanumerico_exemplo_receita(self):
        # Exemplo oficial da Receita Federal: 12.ABC.345/01DE-35
        self.assertTrue(validar_cnpj("12.ABC.345/01DE-35"))
        self.assertTrue(validar_cnpj("12abc34501de35"))
        self.assertFalse(validar_cnpj("12.ABC.345/01DE-36"))
        self.assertEqual(normalizar_cnpj("12.abc.345/01de-35"), "12ABC34501DE35")
        self.assertEqual(formatar_cnpj("12ABC34501DE35"), "12.ABC.345/01DE-35")
        self.assertEqual(formatar_cnpj("11222333000181"), "11.222.333/0001-81")


class TestLike(unittest.TestCase):

    def test_escape(self):
        self.assertEqual(escapar_like("50%_a\\"), "50\\%\\_a\\\\")


if __name__ == "__main__":
    unittest.main()
