"""Extrai lançamentos das faturas em PDF do cartão de crédito Nubank.

Usa pdfplumber para ler a camada de texto do PDF. Se uma página não tiver
texto (PDF escaneado), cai para OCR com Tesseract (pytesseract + pdf2image),
desde que essas dependências estejam instaladas.

Uso:
    python -m financas.nubank_parser financas/data/faturas financas/data/lancamentos.csv
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

import pandas as pd
import pdfplumber

MESES = {
    "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
}

# "30 DEZ •••• 1811 Ciceropaulinoda - Parcela 5/5 R$ 447,47"
# "06 JAN IOF de "Digitalocean.Com" R$ 4,69"
# "05 JAN Pagamento em 05 JAN −R$ 135,00"
LINHA_RE = re.compile(
    r"^(?P<dia>\d{2}) (?P<mes>[A-Z]{3}) "
    r"(?:•+ (?P<cartao>\d{4}) )?"
    r"(?P<descricao>.+?) "
    r"(?P<sinal>[−-])?R\$ (?P<valor>[\d.]+,\d{2})$"
)
VENCIMENTO_RE = re.compile(r"Data de vencimento: (\d{2}) ([A-Z]{3}) (\d{4})")
RESUMO_CAMPOS = {
    "fatura_anterior": r"Fatura anterior R\$ ([\d.]+,\d{2})",
    "pagamento_recebido": r"Pagamento recebido [−-]R\$ ([\d.]+,\d{2})",
    "total_compras": r"Total de compras de todos os cartões.*? R\$ ([\d.]+,\d{2})",
    "iof_internacional": r"IOF de compras internacionais R\$ ([\d.]+,\d{2})",
    "outros_lancamentos": r"Outros lançamentos R\$ ([\d.]+,\d{2})",
    "total_a_pagar": r"Total a pagar R\$ ([\d.]+,\d{2})",
}
PARCELA_RE = re.compile(r"\s+-\s+Parcela (\d+)/(\d+)$")


@dataclass
class Lancamento:
    fatura: str          # vencimento da fatura (YYYY-MM-DD)
    competencia: str     # mês da fatura (YYYY-MM)
    data: str            # data do lançamento (YYYY-MM-DD)
    cartao: str          # final do cartão ("" para Pix/NuPay/encargos)
    descricao: str       # descrição sem o sufixo de parcela
    descricao_original: str
    parcela: int | None
    total_parcelas: int | None
    valor: float         # positivo = débito; negativo = crédito
    tipo: str            # compra | pix_credito | estorno | iof_internacional | encargo | pagamento | ajuste
    arquivo: str


def _valor(txt: str, sinal: str | None) -> float:
    v = float(txt.replace(".", "").replace(",", "."))
    return -v if sinal else v


def _texto_paginas(pdf_path: Path) -> list[str]:
    paginas = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            txt = page.extract_text() or ""
            if len(txt.strip()) < 20:
                txt = _ocr_pagina(pdf_path, i)
            paginas.append(txt)
    return paginas


def _ocr_pagina(pdf_path: Path, indice: int) -> str:
    """Fallback de OCR para páginas sem camada de texto."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:  # pragma: no cover - OCR é opcional
        return ""
    imagens = convert_from_path(str(pdf_path), dpi=300, first_page=indice + 1, last_page=indice + 1)
    return "\n".join(pytesseract.image_to_string(img, lang="por") for img in imagens)


def classificar_tipo(descricao: str, valor: float, secao_pagamentos: bool) -> str:
    d = descricao.lower()
    if d.startswith("pagamento em"):
        return "pagamento"
    if d.startswith(("saldo em atraso", "crédito de atraso", "saldo restante da fatura")):
        return "ajuste"  # movimentações contábeis que se anulam entre faturas
    if d.startswith("iof de \"") or d.startswith("iof de compras"):
        return "iof_internacional"
    if any(k in d for k in ("juros", "multa", "iof de atraso", "iof complementar", "encerramento de dívida")):
        return "encargo"
    if d.startswith(("estorno", "crédito de")) or valor < 0:
        return "estorno"
    if secao_pagamentos:
        return "pix_credito"  # Pix/boleto pago com o limite do cartão
    return "compra"


def _ano_lancamento(mes: int, venc: date) -> int:
    # Lançamentos de meses "à frente" do vencimento pertencem ao ano anterior
    # (ex.: lançamento de DEZ numa fatura que vence em JAN).
    return venc.year - 1 if mes > venc.month else venc.year


def parse_fatura(pdf_path: Path) -> tuple[list[Lancamento], dict]:
    paginas = _texto_paginas(pdf_path)
    tudo = "\n".join(paginas)
    m = VENCIMENTO_RE.search(tudo)
    if not m:
        raise ValueError(f"Vencimento não encontrado em {pdf_path.name}")
    venc = date(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
    meta: dict = {"arquivo": pdf_path.name, "vencimento": venc.isoformat()}
    resumo = tudo.split("RESUMO DA FATURA ATUAL", 1)[-1]
    for campo, padrao in RESUMO_CAMPOS.items():
        rm = re.search(padrao, resumo)
        meta[campo] = _valor(rm.group(1), None) if rm else 0.0

    lancamentos: list[Lancamento] = []
    em_transacoes = False
    secao_pagamentos = False
    for pagina in paginas:
        if "TRANSAÇÕES" not in pagina:
            continue
        em_transacoes = True
        for linha in pagina.splitlines():
            linha = linha.strip()
            if linha.startswith("Pagamentos e Financiamentos"):
                secao_pagamentos = True
                continue
            lm = LINHA_RE.match(linha)
            if not lm:
                continue
            mes = MESES.get(lm.group("mes"))
            if not mes:
                continue
            desc_orig = lm.group("descricao").strip()
            valor = _valor(lm.group("valor"), lm.group("sinal"))
            parcela = total_parc = None
            desc = desc_orig
            pm = PARCELA_RE.search(desc_orig)
            if pm:
                parcela, total_parc = int(pm.group(1)), int(pm.group(2))
                desc = desc_orig[: pm.start()].strip()
            dt = date(_ano_lancamento(mes, venc), mes, int(lm.group("dia")))
            lancamentos.append(Lancamento(
                fatura=venc.isoformat(),
                competencia=f"{venc.year}-{venc.month:02d}",
                data=dt.isoformat(),
                cartao=lm.group("cartao") or "",
                descricao=desc,
                descricao_original=desc_orig,
                parcela=parcela,
                total_parcelas=total_parc,
                valor=valor,
                tipo=classificar_tipo(desc, valor, secao_pagamentos),
                arquivo=pdf_path.name,
            ))
    if not em_transacoes:
        raise ValueError(f"Seção de transações não encontrada em {pdf_path.name}")
    return lancamentos, meta


def parse_pasta(pasta: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    linhas, metas = [], []
    for pdf in sorted(pasta.glob("*.pdf")):
        lancs, meta = parse_fatura(pdf)
        linhas.extend(asdict(l) for l in lancs)
        metas.append(meta)
    return pd.DataFrame(linhas), pd.DataFrame(metas)


def main(argv: list[str]) -> None:
    pasta = Path(argv[1]) if len(argv) > 1 else Path("financas/data/faturas")
    saida = Path(argv[2]) if len(argv) > 2 else Path("financas/data/lancamentos.csv")
    df, meta = parse_pasta(pasta)
    df.to_csv(saida, index=False)
    meta.to_csv(saida.with_name("faturas.csv"), index=False)
    print(f"{len(df)} lançamentos de {len(meta)} faturas -> {saida}")


if __name__ == "__main__":
    main(sys.argv)
