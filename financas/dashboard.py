"""Gera um dashboard HTML autocontido com os gastos do cartão.

Uso:
    python -m financas.dashboard            # lê data/faturas/*.pdf e grava output/dashboard.html
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs

from financas.categorias import aplicar
from financas.nubank_parser import parse_pasta

BASE = Path(__file__).resolve().parent
TIPOS_GASTO = {"compra", "pix_credito", "estorno", "encargo", "iof_internacional"}
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def preparar(pasta: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df, faturas = parse_pasta(pasta)
    df = aplicar(df, BASE / "data" / "categorias_manuais.csv")
    data_dir = BASE / "data"
    df.to_csv(data_dir / "lancamentos.csv", index=False)
    faturas.to_csv(data_dir / "faturas.csv", index=False)
    return df, faturas


def _rotulo_fatura(venc: str) -> str:
    ano, mes, _ = venc.split("-")
    return f"{MESES_PT[int(mes) - 1]}/{ano[2:]}"


def gerar_html(df: pd.DataFrame, faturas: pd.DataFrame) -> str:
    gastos = df[df["tipo"].isin(TIPOS_GASTO)].copy()
    registros = [
        {
            "f": r.fatura, "d": r.data, "desc": r.descricao,
            "parc": f"{int(r.parcela)}/{int(r.total_parcelas)}" if pd.notna(r.parcela) else "",
            "cat": r.categoria, "tipo": r.tipo, "v": round(float(r.valor), 2), "cartao": r.cartao if isinstance(r.cartao, str) else "",
        }
        for r in gastos.itertuples()
    ]
    fats = [
        {"venc": r.vencimento, "rot": _rotulo_fatura(r.vencimento), "total": r.total_a_pagar,
         "pago": r.pagamento_recebido}
        for r in faturas.sort_values("vencimento").itertuples()
    ]
    pagamentos = df[df["tipo"] == "pagamento"][["fatura", "data", "valor"]]
    dados = {
        "lanc": registros,
        "faturas": fats,
        "pagamentos": [{"f": a, "d": b, "v": round(-float(c), 2)} for a, b, c in pagamentos.itertuples(index=False)],
    }
    html = TEMPLATE.replace("/*__PLOTLY__*/", get_plotlyjs())
    return html.replace("/*__DADOS__*/null", json.dumps(dados, ensure_ascii=False))


def main(argv: list[str]) -> None:
    pasta = Path(argv[1]) if len(argv) > 1 else BASE / "data" / "faturas"
    saida = Path(argv[2]) if len(argv) > 2 else BASE / "output" / "dashboard.html"
    df, faturas = preparar(pasta)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(gerar_html(df, faturas), encoding="utf-8")
    print(f"Dashboard gerado em {saida} ({len(df)} lançamentos, {len(faturas)} faturas)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gastos do cartão — Nubank</title>
<script>/*__PLOTLY__*/</script>
<style>
.viz-root {
  color-scheme: light;
  --surface-0: #f5f5f3; --surface-1: #fcfcfb; --border: #e3e2de;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #77756f;
  --grid: #ecebe7;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4; --s6:#008300; --s7:#6250d6; --s8:#e34948;
  --other: #a8a7a1;
  --seq-0:#f0efec; --seq-1:#cde2fb; --seq-2:#86b6ef; --seq-3:#3987e5; --seq-4:#1c5cab; --seq-5:#0d366b;
  --critical: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  .viz-root {
    color-scheme: dark;
    --surface-0: #121211; --surface-1: #1a1a19; --border: #2e2e2c;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #94938b;
    --grid: #2a2a28;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300; --s7:#9085e9; --s8:#e66767;
    --other: #6b6a65;
    --seq-0:#262624; --seq-1:#104281; --seq-2:#1c5cab; --seq-3:#2a78d6; --seq-4:#5598e7; --seq-5:#9ec5f4;
  }
}
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
.viz-root { background: var(--surface-0); color: var(--text-primary); min-height: 100vh; padding: 24px; }
.wrap { max-width: 1200px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px; }
.sub { color: var(--text-secondary); margin: 0 0 20px; }
.filters { display: flex; flex-wrap: wrap; gap: 12px; align-items: end; margin-bottom: 20px; }
.filters label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--text-secondary); }
select, input { font: inherit; padding: 6px 10px; border: 1px solid var(--border); border-radius: 8px;
  background: var(--surface-1); color: var(--text-primary); min-width: 180px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 16px; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.kpi .lbl { font-size: 12px; color: var(--text-secondary); }
.kpi .val { font-size: 26px; font-weight: 600; margin-top: 4px; font-variant-numeric: tabular-nums; }
.kpi .note { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.kpi.alert .val::before { content: "⚠ "; color: var(--critical); font-size: 20px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
.full { grid-column: 1 / -1; }
@media (max-width: 860px) { .grid { grid-template-columns: 1fr; } }
.card h2 { font-size: 15px; margin: 0 0 2px; }
.card .desc { font-size: 12px; color: var(--text-secondary); margin: 0 0 8px; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); font-size: 13px; }
th { color: var(--text-secondary); font-weight: 600; position: sticky; top: 0; background: var(--surface-1); cursor: pointer; }
td.num, th.num { text-align: right; }
.tbl-wrap { max-height: 480px; overflow: auto; }
.muted { color: var(--text-muted); }
.foot { color: var(--text-muted); font-size: 12px; margin-top: 16px; }
</style>
</head>
<body>
<div class="viz-root">
<div class="wrap">
  <h1>Para onde foi o dinheiro do cartão</h1>
  <p class="sub">Cartão de crédito Nubank · Leonardo Vinícius Nunes de Oliveira · faturas extraídas dos PDFs enviados por e-mail</p>

  <div class="filters">
    <label>Fatura (vencimento)<select id="fFatura"></select></label>
    <label>Categoria<select id="fCat"></select></label>
    <label>Buscar estabelecimento<input id="fBusca" type="search" placeholder="ex.: ifood, posto…"></label>
  </div>

  <div class="kpis" id="kpis"></div>

  <div class="grid">
    <div class="card">
      <h2>Gasto por categoria</h2><p class="desc">Soma no período filtrado, em R$</p>
      <div id="chCat" style="height:520px"></div>
    </div>
    <div class="card">
      <h2>Maiores estabelecimentos</h2><p class="desc">Top 15 por valor no período filtrado, em R$</p>
      <div id="chTop" style="height:520px"></div>
    </div>
    <div class="card full">
      <h2>Gasto por fatura</h2><p class="desc">Cada barra é uma fatura (mês de vencimento), dividida pelas 7 maiores categorias + outras</p>
      <div id="chMes" style="height:400px"></div>
    </div>
    <div class="card full">
      <h2>Categoria × mês</h2><p class="desc">Quanto mais escuro, mais gasto naquela categoria naquela fatura</p>
      <div id="chHeat" style="height:560px"></div>
    </div>
    <div class="card full">
      <h2>Lançamentos</h2><p class="desc" id="tblInfo"></p>
      <div class="tbl-wrap"><table id="tbl"><thead><tr>
        <th data-k="f">Fatura</th><th data-k="d">Data</th><th data-k="desc">Descrição</th><th data-k="parc">Parcela</th>
        <th data-k="cat">Categoria</th><th data-k="v" class="num">Valor</th></tr></thead><tbody></tbody></table></div>
    </div>
  </div>
  <p class="foot">Valores positivos são débitos; estornos aparecem negativos. "Pix no crédito" = Pix/boleto pago com o limite do cartão.
  Lançamentos contábeis de atraso ("Saldo em atraso"/"Crédito de atraso") se anulam e foram excluídos; juros, multas e IOF estão na categoria própria.
  Os totais por fatura conferem com o "Total a pagar" de cada PDF.</p>
</div>
</div>
<script>
const DADOS = /*__DADOS__*/null;
const css = n => getComputedStyle(document.querySelector('.viz-root')).getPropertyValue(n).trim();
const brl = v => v.toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
const brl0 = v => v.toLocaleString('pt-BR', {style:'currency', currency:'BRL', maximumFractionDigits:0});
const rotFat = Object.fromEntries(DADOS.faturas.map(f => [f.venc, f.rot]));
const ENC = 'Juros, multas e IOF';

// cor fixa por categoria (segue a entidade, nunca o ranking): ordem pelo total geral
const totGeral = {};
DADOS.lanc.forEach(l => totGeral[l.cat] = (totGeral[l.cat]||0) + l.v);
const catsOrd = Object.keys(totGeral).sort((a,b) => totGeral[b]-totGeral[a]);
const TOPCATS = catsOrd.slice(0, 7);
const corCat = c => { const i = TOPCATS.indexOf(c); return i >= 0 ? css('--s'+(i+1)) : css('--other'); };

const fF = document.getElementById('fFatura'), fC = document.getElementById('fCat'), fB = document.getElementById('fBusca');
fF.innerHTML = '<option value="">Todas as faturas</option>' + DADOS.faturas.map(f => `<option value="${f.venc}">${f.rot} (vence ${f.venc.split('-').reverse().join('/')})</option>`).join('');
fC.innerHTML = '<option value="">Todas as categorias</option>' + catsOrd.map(c => `<option>${c}</option>`).join('');

function filtrados(ignorarFatura=false) {
  const q = fB.value.trim().toLowerCase();
  return DADOS.lanc.filter(l => (ignorarFatura || !fF.value || l.f === fF.value)
    && (!fC.value || l.cat === fC.value) && (!q || l.desc.toLowerCase().includes(q)));
}
const soma = (arr, k) => { const o = {}; arr.forEach(l => o[k(l)] = (o[k(l)]||0) + l.v); return o; };

function layoutBase(extra={}) {
  return Object.assign({
    paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
    font: {family: 'system-ui, sans-serif', size: 12, color: css('--text-secondary')},
    margin: {l: 10, r: 20, t: 10, b: 40},
    hoverlabel: {bgcolor: css('--surface-1'), bordercolor: css('--border'), font: {color: css('--text-primary')}},
    xaxis: {gridcolor: css('--grid'), zeroline: false, automargin: true},
    yaxis: {gridcolor: css('--grid'), zeroline: false, automargin: true},
  }, extra);
}
const CFG = {displayModeBar: false, responsive: true, locale: 'pt-BR'};

function kpis(rows) {
  const total = rows.reduce((s,l) => s+l.v, 0);
  const enc = rows.filter(l => l.cat === ENC).reduce((s,l) => s+l.v, 0);
  const nFat = new Set(rows.map(l => l.f)).size || 1;
  const porCat = soma(rows.filter(l => l.cat !== ENC), l => l.cat);
  const top = Object.entries(porCat).sort((a,b) => b[1]-a[1])[0];
  const parcelado = rows.filter(l => l.parc).reduce((s,l) => s+l.v, 0);
  const tiles = [
    ['Total gasto no cartão', brl(total), `${rows.length} lançamentos em ${nFat} fatura(s)`],
    ['Média por fatura', brl(total/nFat), 'total ÷ nº de faturas'],
    ['Maior categoria', top ? top[0] : '—', top ? brl(top[1]) + ` (${(100*top[1]/total).toFixed(0)}%)` : ''],
    ['Compras parceladas', brl(parcelado), `${(100*parcelado/(total||1)).toFixed(0)}% do total`],
    ['Juros, multas e IOF', brl(enc), 'custo de atraso / câmbio — evitável', enc > 0],
  ];
  document.getElementById('kpis').innerHTML = tiles.map(([l,v,n,a]) =>
    `<div class="card kpi${a?' alert':''}"><div class="lbl">${l}</div><div class="val">${v}</div><div class="note">${n}</div></div>`).join('');
}

function chCat(rows) {
  const o = Object.entries(soma(rows, l => l.cat)).sort((a,b) => a[1]-b[1]);
  Plotly.react('chCat', [{
    type: 'bar', orientation: 'h', x: o.map(e => e[1]), y: o.map(e => e[0]),
    marker: {color: css('--s1'), line: {color: css('--surface-1'), width: 2}},
    text: o.map(e => brl0(e[1])), textposition: 'outside', cliponaxis: false,
    textfont: {color: css('--text-secondary')},
    hovertemplate: '%{y}<br><b>%{x:$,.2f}</b><extra></extra>',
  }], layoutBase({xaxis: {visible: false}, yaxis: {automargin: true, color: css('--text-primary')}, margin: {l: 10, r: 70, t: 0, b: 0}, bargap: 0.3}), CFG);
}

function chTop(rows) {
  const o = Object.entries(soma(rows.filter(l => l.cat !== ENC), l => l.desc)).sort((a,b) => b[1]-a[1]).slice(0, 15).reverse();
  const catDe = Object.fromEntries(rows.map(l => [l.desc, l.cat]));
  Plotly.react('chTop', [{
    type: 'bar', orientation: 'h', x: o.map(e => e[1]), y: o.map(e => e[0]),
    marker: {color: css('--s1'), line: {color: css('--surface-1'), width: 2}},
    text: o.map(e => brl0(e[1])), textposition: 'outside', cliponaxis: false,
    textfont: {color: css('--text-secondary')}, customdata: o.map(e => catDe[e[0]]),
    hovertemplate: '%{y}<br>%{customdata}<br><b>%{x:$,.2f}</b><extra></extra>',
  }], layoutBase({xaxis: {visible: false}, yaxis: {automargin: true, color: css('--text-primary')}, margin: {l: 10, r: 70, t: 0, b: 0}, bargap: 0.3}), CFG);
}

function chMes(rows) {
  const fats = DADOS.faturas.map(f => f.venc);
  const grupos = [...TOPCATS, 'Outras categorias'];
  const g = l => TOPCATS.includes(l.cat) ? l.cat : 'Outras categorias';
  const traces = grupos.map(c => {
    const por = soma(rows.filter(l => g(l) === c), l => l.f);
    return {type: 'bar', name: c, x: fats.map(f => rotFat[f]), y: fats.map(f => por[f]||0),
      marker: {color: c === 'Outras categorias' ? css('--other') : corCat(c), line: {color: css('--surface-1'), width: 1}},
      hovertemplate: `${c}<br>%{x}: <b>%{y:$,.2f}</b><extra></extra>`};
  }).filter(t => t.y.some(v => v !== 0));
  const totais = fats.map(f => rows.filter(l => l.f === f).reduce((s,l) => s+l.v, 0));
  traces.push({type: 'scatter', mode: 'text', x: fats.map(f => rotFat[f]), y: totais, text: totais.map(brl0),
    textposition: 'top center', textfont: {color: css('--text-primary'), size: 11}, showlegend: false, hoverinfo: 'skip'});
  Plotly.react('chMes', traces, layoutBase({barmode: 'relative', bargap: 0.35,
    legend: {orientation: 'h', y: -0.15, font: {color: css('--text-secondary')}},
    yaxis: {gridcolor: css('--grid'), tickprefix: 'R$ ', tickformat: ',.0f', automargin: true}, separators: ',.', margin: {l: 70, r: 10, t: 20, b: 10}}), CFG);
}

function chHeat(rows) {
  const fats = DADOS.faturas.map(f => f.venc);
  const cats = catsOrd.filter(c => rows.some(l => l.cat === c)).slice().reverse();
  const z = cats.map(c => fats.map(f => {
    const v = rows.filter(l => l.cat === c && l.f === f).reduce((s,l) => s+l.v, 0); return Math.round(v*100)/100; }));
  const scale = [0, .1, .3, .55, .8, 1].map((p,i) => [p, css('--seq-'+i)]);
  Plotly.react('chHeat', [{
    type: 'heatmap', z, x: fats.map(f => rotFat[f]), y: cats, colorscale: scale, xgap: 2, ygap: 2,
    hovertemplate: '%{y}<br>%{x}: <b>%{z:$,.2f}</b><extra></extra>',
    colorbar: {thickness: 10, outlinewidth: 0, tickprefix: 'R$ ', tickfont: {color: css('--text-secondary')}},
  }], layoutBase({xaxis: {side: 'top', color: css('--text-secondary')}, yaxis: {automargin: true, color: css('--text-primary')}, margin: {l: 10, r: 10, t: 30, b: 10}}), CFG);
}

let ordem = {k: 'd', asc: false};
function tabela(rows) {
  const r = rows.slice().sort((a,b) => { const x = a[ordem.k], y = b[ordem.k];
    return (x < y ? -1 : x > y ? 1 : 0) * (ordem.asc ? 1 : -1); });
  document.querySelector('#tbl tbody').innerHTML = r.map(l => `<tr><td>${rotFat[l.f]}</td><td>${l.d.split('-').reverse().join('/')}</td>
    <td>${l.desc}${l.tipo==='pix_credito'?' <span class="muted">(Pix no crédito)</span>':''}</td><td class="muted">${l.parc}</td>
    <td>${l.cat}</td><td class="num">${brl(l.v)}</td></tr>`).join('');
  document.getElementById('tblInfo').textContent = `${r.length} lançamentos · total ${brl(r.reduce((s,l)=>s+l.v,0))} · clique no cabeçalho para ordenar`;
}
document.querySelectorAll('#tbl th').forEach(th => th.onclick = () => {
  ordem = {k: th.dataset.k, asc: ordem.k === th.dataset.k ? !ordem.asc : th.dataset.k !== 'v' && th.dataset.k !== 'd'}; render(); });

function render() {
  const rows = filtrados();
  kpis(rows); chCat(rows); chTop(rows); chMes(filtrados(true)); chHeat(filtrados(true)); tabela(rows);
}
[fF, fC].forEach(e => e.onchange = render); fB.oninput = render;
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);
render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main(sys.argv)
