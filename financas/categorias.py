"""Categorização dos lançamentos por regras de palavra-chave.

As regras são avaliadas em ordem; a primeira que casar vence. Para corrigir
uma categoria, basta adicionar/ajustar uma regra aqui (ou em
`data/categorias_manuais.csv`, que tem prioridade sobre as regras).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

REGRAS: list[tuple[str, list[str]]] = [
    ("Juros, multas e IOF", [
        r"juros", r"multa", r"iof", r"encerramento de divida",
    ]),
    ("Assinaturas e tecnologia", [
        r"claude\.ai", r"openai", r"chatgpt", r"elevenlabs", r"digitalocean", r"google one",
        r"youtube", r"netflix", r"paramount", r"disney", r"canva", r"hostinger", r"linkedin",
        r"jusbrasil", r"\bmesh\b", r"synapse digital", r"serasa", r"amazon prime",
    ]),
    ("Telefone e internet", [r"tim\*tim", r"\btim\b", r"mhnet"]),
    ("Educação e cursos", [
        r"asimov", r"hotmart", r"tutorials dojo", r"rocketseat", r"mundial formaturas",
        r"livraria", r"monetizze", r"alura", r"udemy",
    ]),
    ("Delivery (iFood)", [r"ifood", r"\bifd\*"]),
    ("Transporte por app (99/Uber)", [r"^99 ", r"estorno de 99", r"uber"]),
    ("Combustível", [r"auto ?posto", r"auto po\b", r"postodapraca", r"posto\b", r"stefanello"]),
    ("Veículo (manutenção/despachante)", [
        r"funilaria", r"conter motos", r"autocar", r"autocred", r"despachante",
    ]),
    ("Viagens", [
        r"gol linhas", r"\bibis\b", r"eucatur", r"aeroporto", r"latam", r"azul linhas",
        r"ciceropaulino",
    ]),
    ("Supermercado", [
        r"supermercado", r"mercado", r"amigao", r"\bc vale\b", r"cestao", r"fogo atacadista",
        r"mercearia", r"minibox", r"distribuidora", r"cordil", r"jchagas alimentos",
        r"preco leve(?! confec)", r"macau",
    ]),
    ("Padaria, lanches e restaurantes", [
        r"panificadora", r"pizzaria", r"lanches", r"sorvete", r"cremolatte", r"acai",
        r"churros", r"garapeira", r"dogburger", r"estacao sabores", r"salgados",
        r"casarao oriental", r"cacau show", r"paixao mineira", r"espeto", r"restaura",
        r"conveni", r"pao vinho", r"rasta e jopa", r"top m\b",
    ]),
    ("Saúde e farmácia", [
        r"drog", r"farmacia", r"raia", r"ultra popular", r"laborat", r"navilabor",
        r"centro medico", r"fuzafarma", r"corpo e saude",
    ]),
    ("Pets", [r"pet ?shop", r"villa pet", r"veterinari", r"animais"]),
    ("Beleza e cuidados pessoais", [
        r"cosmetic", r"boticario", r"sobrancelha", r"cabeleire", r"estudio", r"biju",
    ]),
    ("Casa e construção", [
        r"materiais", r"parafusos", r"epis\b", r"fazendeiro", r"lavo navirai", r"embalagens",
        r"utilidad", r"armazem 1,99",
    ]),
    ("Compras (lojas, eletrônicos, vestuário)", [
        r"americanas", r"mercadoli", r"amazon", r"loja", r"xing ling", r"cresci e perdi",
        r"confeccoes", r"hiper festa", r"celulares", r"informatica", r"xarmizie",
        r"incendiaria", r"giusti",
    ]),
    ("Doações, igreja e associações", [r"igreja", r"mbl movimento", r"movimento brasil livre"]),
    ("Serviços e eventos", [r"bgn servicos", r"parquedeexpos", r"wiinpay", r"sqalapay"]),
]

_REGRAS_COMPILADAS = [(cat, [re.compile(p) for p in pats]) for cat, pats in REGRAS]


def _normalizar(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    return txt.lower().strip()


def categorizar(descricao: str, tipo: str) -> str:
    if tipo in ("encargo", "iof_internacional"):
        return "Juros, multas e IOF"
    d = _normalizar(descricao)
    d = re.sub(r'^(estorno de|credito de) "?', "", d).rstrip('"')
    for cat, pats in _REGRAS_COMPILADAS:
        if any(p.search(d) for p in pats):
            return cat
    # Pix/maquininha de pessoa física (nomes próprios, MEI com CPF/CNPJ no início)
    return "Pessoas e Pix (a identificar)"


def aplicar(df: pd.DataFrame, manuais: Path | None = None) -> pd.DataFrame:
    df = df.copy()
    df["categoria"] = [categorizar(d, t) for d, t in zip(df["descricao"], df["tipo"])]
    if manuais and manuais.exists():
        m = pd.read_csv(manuais)  # colunas: descricao,categoria
        mapa = dict(zip(m["descricao"], m["categoria"]))
        df["categoria"] = df["descricao"].map(mapa).fillna(df["categoria"])
    return df
