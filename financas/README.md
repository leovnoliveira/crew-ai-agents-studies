# Finanças pessoais — extrator de faturas + dashboard

Extrai os lançamentos das faturas em PDF do cartão **Nubank** e gera um dashboard HTML
(autocontido, funciona offline) mostrando para onde foi o dinheiro.

## Como usar

```bash
pip install -r financas/requirements.txt
# coloque os PDFs das faturas em financas/data/faturas/
python -m financas.dashboard
# abra financas/output/dashboard.html no navegador
```

Também gera `financas/data/lancamentos.csv` (um lançamento por linha, já categorizado)
e `financas/data/faturas.csv` (resumo de cada fatura).

## Como funciona

- `nubank_parser.py` — lê o texto dos PDFs com **pdfplumber**; se uma página não tiver
  texto (PDF escaneado), usa **OCR com Tesseract** (`pytesseract` + `pdf2image`).
  Classifica cada linha em `compra`, `pix_credito`, `estorno`, `iof_internacional`,
  `encargo` (juros/multa), `pagamento` ou `ajuste` (lançamentos contábeis de atraso que se anulam).
- `categorias.py` — regras por palavra-chave (Supermercado, Combustível, Assinaturas…).
  Para corrigir, edite as regras ou crie `financas/data/categorias_manuais.csv`
  com as colunas `descricao,categoria` (tem prioridade sobre as regras).
- `dashboard.py` — monta o HTML com Plotly: KPIs, gasto por categoria, maiores
  estabelecimentos, gasto por fatura, mapa categoria × mês e tabela filtrável.

Conferência: para cada fatura, a soma dos lançamentos extraídos bate com o
"Total a pagar" do PDF (descontado o saldo da fatura anterior).

## Privacidade

Este repositório é público: `financas/.gitignore` impede que PDFs, CSVs e o dashboard
gerado sejam commitados. Só o código fica versionado.

## Próximos passos

- Importar os extratos da PJ (LN Data System) e da conta PF para cruzar
  pró-labore / distribuição de lucros → pagamento das faturas.
