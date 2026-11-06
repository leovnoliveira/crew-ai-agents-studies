from datetime import date

from financas.categorias import categorizar
from financas.nubank_parser import LINHA_RE, _ano_lancamento, classificar_tipo


def test_linha_compra_parcelada():
    m = LINHA_RE.match("30 DEZ •••• 1811 Gol Linhas Aereas S.A. - Parcela 2/5 R$ 70,40")
    assert m and m["cartao"] == "1811" and m["valor"] == "70,40"


def test_linha_credito():
    m = LINHA_RE.match("05 JAN Pagamento em 05 JAN −R$ 135,00")
    assert m and m["sinal"] == "−" and m["cartao"] is None


def test_ano_virada():
    assert _ano_lancamento(12, date(2026, 1, 6)) == 2025
    assert _ano_lancamento(1, date(2026, 2, 6)) == 2026


def test_tipos():
    assert classificar_tipo("Pagamento em 12 JAN", -10, True) == "pagamento"
    assert classificar_tipo("Saldo em atraso", 10, True) == "ajuste"
    assert classificar_tipo("Juros de atraso", 10, True) == "encargo"
    assert classificar_tipo("EDUARDO VANSSO BARBOSA", 10, True) == "pix_credito"
    assert classificar_tipo("C Vale", 10, False) == "compra"


def test_categorias():
    assert categorizar("Supermercado Chama", "compra") == "Supermercado"
    assert categorizar("Claude.Ai Subscription", "compra") == "Assinaturas e tecnologia"
    assert categorizar("Auto Posto Faleiros", "compra") == "Combustível"
    assert categorizar("iFood - NuPay", "compra") == "Delivery (iFood)"
