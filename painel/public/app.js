// Painel do lab: conversa com os 4 microserviços pelo proxy /api/<serviço>/ do nginx.
const SERVICOS = [
  { id: 'items', nome: 'items-service', porta: 8383, pagina: 'itens', lista: '/itens', conta: (d) => d.itens.length, rotulo: 'itens' },
  { id: 'lojas', nome: 'lojas-service', porta: 8282, pagina: 'lojas', lista: '/lojas', conta: (d) => d.lojas.length, rotulo: 'lojas' },
  { id: 'pedidos', nome: 'pedidos-service', porta: 8080, pagina: 'pedidos', lista: '/pedidos', conta: (d) => d.length, rotulo: 'pedidos' },
  { id: 'pagamentos', nome: 'pagamentos-service', porta: 8181, pagina: 'pagamentos', lista: '/historico', conta: (d) => d.historico.length, rotulo: 'transações' },
];
const STATUS_PEDIDO = ['em processamento', 'pago', 'enviado', 'entregue', 'cancelado'];
const FORMAS = { cartao_credito: 'Cartão de crédito', boleto: 'Boleto', pix: 'PIX' };

const $ = (sel, el = document) => el.querySelector(sel);
const brl = (v) => (v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const cls = (s) => 's-' + String(s).replace(/\s+/g, '-');
const ROTULO = { pending: 'pendente', succeeded: 'aprovado' };
const pill = (s) => `<span class="pill ${cls(s)}">${esc(ROTULO[s] || s)}</span>`;
const quando = (iso) => (iso ? new Date(iso + 'Z').toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '');
const forma = (f) => FORMAS[f] || f;

async function api(servico, caminho, opcoes = {}) {
  const init = { method: opcoes.method || 'GET', headers: {} };
  if (opcoes.body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(opcoes.body);
  }
  const resp = await fetch(`/api/${servico}${caminho}`, init);
  let data = null;
  try { data = await resp.json(); } catch { /* corpo vazio */ }
  if (!resp.ok) throw new Error((data && (data.message || data.error)) || `${servico}: HTTP ${resp.status}`);
  return data;
}

function toast(msg, erro = false) {
  const el = document.createElement('div');
  el.className = 'toast' + (erro ? ' erro' : '');
  el.textContent = msg;
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), 3600);
}

const tentar = (fn) => async (...args) => {
  try { await fn(...args); } catch (e) { toast(e.message, true); }
};

function tabela(colunas, linhas, vazio) {
  if (!linhas.length) return `<p class="empty">${vazio}</p>`;
  const th = colunas.map((c) => `<th class="${c.cls || ''}">${c.t}</th>`).join('');
  const tr = linhas.map((l) => `<tr>${colunas.map((c) => `<td class="${c.cls || ''}">${c.v(l)}</td>`).join('')}</tr>`).join('');
  return `<table><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table>`;
}

// ---------- Navegação ----------
const PAGINAS = { visao: carregarVisao, itens: carregarItens, lojas: carregarLojas, pedidos: carregarPedidos, pagamentos: carregarPagamentos };

function navegar() {
  const pagina = (location.hash || '#visao').slice(1);
  const atual = PAGINAS[pagina] ? pagina : 'visao';
  document.querySelectorAll('.page').forEach((p) => { p.hidden = p.id !== `page-${atual}`; });
  document.querySelectorAll('nav a').forEach((a) => a.classList.toggle('active', a.dataset.page === atual));
  tentar(PAGINAS[atual])();
  atualizarSaude();
}

async function atualizarSaude() {
  await Promise.all(SERVICOS.map(async (s) => {
    let ok = false;
    try { ok = (await api(s.id, '/status')).status === 'ok'; } catch { ok = false; }
    document.querySelectorAll(`.dot[data-svc="${s.id}"]`).forEach((d) => { d.className = 'dot ' + (ok ? 'up' : 'down'); });
  }));
}

// ---------- Visão geral ----------
async function carregarVisao() {
  const cards = await Promise.all(SERVICOS.map(async (s) => {
    let ok = false, total = '·';
    try { ok = (await api(s.id, '/status')).status === 'ok'; } catch { /* fora do ar */ }
    try { total = s.conta(await api(s.id, s.lista)); } catch { /* fora do ar */ }
    return `<a class="svc" href="#${s.pagina}">
      <div class="svc-top"><span class="svc-name">${s.nome}</span><span class="state ${ok ? 'up' : 'down'}">${ok ? 'online' : 'fora do ar'}</span></div>
      <div class="svc-count">${total}<small>${s.rotulo}</small></div>
      <div class="svc-meta"><span>:${s.porta}</span><span>${s.id}_db</span></div>
    </a>`;
  }));
  $('#svc-grid').innerHTML = cards.join('');
  let pedidos = [];
  try { pedidos = (await api('pedidos', '/pedidos')).slice(0, 5); } catch { /* fora do ar */ }
  $('#ultimos-pedidos').innerHTML = tabela([
    { t: 'Nº', cls: 'id', v: (p) => p.id },
    { t: 'Cliente', v: (p) => `cliente ${p.cliente_id}` },
    { t: 'Itens', v: (p) => p.itens.reduce((n, i) => n + i.quantidade, 0) },
    { t: 'Pagamento', v: (p) => forma(p.forma_pagamento) },
    { t: 'Status', v: (p) => pill(p.status) },
    { t: 'Total', cls: 'num', v: (p) => brl(p.total) },
  ], pedidos, 'Nenhum pedido ainda. Cadastre itens e crie um pedido.');
}

// ---------- Itens ----------
async function carregarItens() {
  const { itens } = await api('items', '/itens');
  $('#tabela-itens').innerHTML = tabela([
    { t: 'ID', cls: 'id', v: (i) => i.id },
    { t: 'Nome', v: (i) => `<b>${esc(i.nome)}</b>` },
    { t: 'Descrição', v: (i) => `<small>${esc(i.descricao)}</small>` },
    { t: 'Preço', cls: 'num', v: (i) => brl(i.preco) },
    { t: '', cls: 'actions', v: (i) => `<button class="btn small danger" data-remover="${i.id}">Remover</button>` },
  ], itens, 'Nenhum item cadastrado.');
}

$('#form-item').addEventListener('submit', tentar(async (e) => {
  e.preventDefault();
  const f = e.target;
  const body = Object.fromEntries(new FormData(f));
  const { message } = await api('items', '/itens', { method: 'POST', body });
  toast(message);
  f.reset();
  f.nome.focus();
  await carregarItens();
}));

$('#tabela-itens').addEventListener('click', tentar(async (e) => {
  const id = e.target.dataset.remover;
  if (!id) return;
  const { message } = await api('items', `/itens/${id}`, { method: 'DELETE' });
  toast(message);
  await carregarItens();
}));

// ---------- Lojas ----------
let lojaAtual = null;

async function carregarLojas() {
  const { lojas } = await api('lojas', '/lojas');
  if (!lojaAtual && lojas.length) lojaAtual = lojas[0].id;
  $('#lista-lojas').innerHTML = lojas.length
    ? lojas.map((l) => `<button class="loja-btn ${l.id === lojaAtual ? 'active' : ''}" data-loja="${l.id}"><b>${esc(l.nome)}</b><small>${esc(l.endereco) || 'sem endereço'}</small></button>`).join('')
    : '<p class="empty" style="padding:0 8px">Nenhuma loja cadastrada.</p>';
  if (lojaAtual) await carregarDashboard(lojaAtual);
}

async function carregarDashboard(id) {
  const [d, { itens }] = await Promise.all([api('lojas', `/dashboard/${id}`), api('items', '/itens')]);
  const unidades = d.estoque.reduce((n, e) => n + e.estoque, 0);
  $('#dashboard-loja').innerHTML = `
    <div class="card-head"><h2>${esc(d.loja.nome)}</h2><small class="mono">GET /dashboard/${d.loja.id}</small></div>
    <small>${esc(d.loja.endereco)}${d.loja.contato ? ' · ' + esc(d.loja.contato) : ''}</small>
    <div class="kpis">
      <div class="kpi"><span>Faturamento</span><b>${brl(d.faturamento)}</b></div>
      <div class="kpi"><span>Pedidos</span><b>${d.vendas.length}</b></div>
      <div class="kpi"><span>Unidades em estoque</span><b>${unidades}</b></div>
    </div>
    ${d.avisos.map((a) => `<p class="empty">${esc(a)}</p>`).join('')}
    <p class="sub">Estoque</p>
    ${tabela([
      { t: 'Item', v: (e) => `<b>${esc(e.nome || 'item ' + e.produto_id)}</b>` },
      { t: 'Preço', cls: 'num', v: (e) => brl(e.preco) },
      { t: 'Estoque', cls: 'num', v: (e) => e.estoque },
    ], d.estoque, 'Nenhum item associado a esta loja.')}
    <form class="assoc" id="form-assoc">
      <label>Associar item<select name="produto_id">${itens.map((i) => `<option value="${i.id}">${esc(i.nome)}</option>`).join('')}</select></label>
      <label class="w-sm">Estoque<input name="estoque" type="number" min="0" value="10" required></label>
      <button class="btn ghost" ${itens.length ? '' : 'disabled'}>Associar</button>
    </form>
    <p class="sub">Vendas</p>
    ${tabela([
      { t: 'Nº', cls: 'id', v: (p) => p.id },
      { t: 'Cliente', v: (p) => `cliente ${p.cliente_id}` },
      { t: 'Status', v: (p) => pill(p.status) },
      { t: 'Total', cls: 'num', v: (p) => brl(p.total) },
    ], d.vendas, 'Nenhum pedido para esta loja.')}`;
  $('#form-assoc').addEventListener('submit', tentar(async (e) => {
    e.preventDefault();
    const body = { loja_id: id, ...Object.fromEntries(new FormData(e.target)) };
    const { message } = await api('lojas', '/produtos_lojas', { method: 'POST', body });
    toast(message);
    await carregarDashboard(id);
  }));
}

$('#form-loja').addEventListener('submit', tentar(async (e) => {
  e.preventDefault();
  const f = e.target;
  const data = await api('lojas', '/lojas', { method: 'POST', body: Object.fromEntries(new FormData(f)) });
  toast(data.message);
  lojaAtual = data.loja_id;
  f.reset();
  await carregarLojas();
}));

$('#lista-lojas').addEventListener('click', tentar(async (e) => {
  const btn = e.target.closest('[data-loja]');
  if (!btn) return;
  lojaAtual = Number(btn.dataset.loja);
  document.querySelectorAll('.loja-btn').forEach((b) => b.classList.toggle('active', b === btn));
  await carregarDashboard(lojaAtual);
}));

// ---------- Pedidos ----------
let catalogo = [];

function novaLinha() {
  const div = document.createElement('div');
  div.className = 'linha';
  div.innerHTML = `
    <label>Item<select name="produto_id">${catalogo.map((i) => `<option value="${i.id}">${esc(i.nome)} · ${brl(i.preco)}</option>`).join('')}</select></label>
    <label class="w-sm">Quantidade<input name="quantidade" type="number" min="1" value="1" required></label>
    <button type="button" class="btn small danger" data-tirar>Tirar</button>`;
  $('#linhas-pedido').appendChild(div);
  estimar();
}

function estimar() {
  let total = 0;
  document.querySelectorAll('#linhas-pedido .linha').forEach((l) => {
    const item = catalogo.find((i) => i.id === Number($('select', l).value));
    total += (item ? item.preco : 0) * (Number($('input', l).value) || 0);
  });
  $('#estimativa').textContent = brl(total);
}

async function opcoesFormas(select) {
  const { formas_pagamento } = await api('pagamentos', '/formas_pagamento');
  select.innerHTML = formas_pagamento.map((f) => `<option value="${esc(f)}">${esc(forma(f))}</option>`).join('');
}

async function carregarPedidos() {
  const [{ itens }, { lojas }, pedidos] = await Promise.all([api('items', '/itens'), api('lojas', '/lojas'), api('pedidos', '/pedidos')]);
  catalogo = itens;
  $('#pedido-loja').innerHTML = '<option value="">sem loja</option>' + lojas.map((l) => `<option value="${l.id}">${esc(l.nome)}</option>`).join('');
  await opcoesFormas($('#pedido-forma'));
  $('#linhas-pedido').innerHTML = '';
  if (catalogo.length) novaLinha(); else $('#linhas-pedido').innerHTML = '<p class="empty">Cadastre itens antes de criar um pedido.</p>';
  const nomes = Object.fromEntries(itens.map((i) => [i.id, i.nome]));
  const lojaNome = Object.fromEntries(lojas.map((l) => [l.id, l.nome]));
  $('#tabela-pedidos').innerHTML = tabela([
    { t: 'Nº', cls: 'id', v: (p) => p.id },
    { t: 'Cliente', v: (p) => `cliente ${p.cliente_id}<br><small>${esc(lojaNome[p.loja_id] || 'sem loja')}</small>` },
    { t: 'Itens', v: (p) => p.itens.map((i) => `${i.quantidade}× ${esc(nomes[i.produto_id] || 'item ' + i.produto_id)}`).join('<br>') },
    { t: 'Pagamento', v: (p) => forma(p.forma_pagamento) },
    { t: 'Criado', v: (p) => `<small>${quando(p.data_criacao)}</small>` },
    { t: 'Total', cls: 'num', v: (p) => brl(p.total) },
    { t: 'Status', cls: 'actions', v: (p) => `<select class="status" data-pedido="${p.id}">${STATUS_PEDIDO.map((s) => `<option ${s === p.status ? 'selected' : ''}>${s}</option>`).join('')}</select>` },
  ], pedidos, 'Nenhum pedido ainda.');
}

$('#add-linha').addEventListener('click', () => catalogo.length && novaLinha());
$('#linhas-pedido').addEventListener('input', estimar);
$('#linhas-pedido').addEventListener('click', (e) => {
  if (e.target.dataset.tirar !== undefined && document.querySelectorAll('#linhas-pedido .linha').length > 1) {
    e.target.closest('.linha').remove();
    estimar();
  }
});

$('#form-pedido').addEventListener('submit', tentar(async (e) => {
  e.preventDefault();
  const f = e.target;
  const itens = [...document.querySelectorAll('#linhas-pedido .linha')].map((l) => ({
    produto_id: Number($('select', l).value), quantidade: Number($('input', l).value),
  }));
  const body = { cliente_id: Number(f.cliente_id.value), loja_id: f.loja_id.value || null, forma_pagamento: f.forma_pagamento.value, itens };
  const pedido = await api('pedidos', '/pedidos', { method: 'POST', body });
  toast(`Pedido ${pedido.id} criado: ${brl(pedido.total)}`);
  await carregarPedidos();
}));

$('#tabela-pedidos').addEventListener('change', tentar(async (e) => {
  const id = e.target.dataset.pedido;
  if (!id) return;
  const r = await api('pedidos', `/pedidos/${id}/status`, { method: 'PUT', body: { status: e.target.value } });
  toast(`Pedido ${r.id}: ${r.status}`);
}));

// ---------- Pagamentos ----------
async function carregarPagamentos() {
  const [pedidos, { historico }] = await Promise.all([api('pedidos', '/pedidos'), api('pagamentos', '/historico')]);
  const abertos = pedidos.filter((p) => p.status === 'em processamento');
  $('#pag-pedido').innerHTML = abertos.length
    ? abertos.map((p) => `<option value="${p.id}" data-forma="${esc(p.forma_pagamento)}">Pedido ${p.id} · cliente ${p.cliente_id} · ${brl(p.total)}</option>`).join('')
    : '<option value="">nenhum pedido em processamento</option>';
  await opcoesFormas($('#pag-forma'));
  sugerirForma();
  $('#tabela-transacoes').innerHTML = tabela([
    { t: 'ID', cls: 'id', v: (t) => t.id },
    { t: 'Pedido', cls: 'nowrap', v: (t) => (t.pedido_id ? `pedido ${t.pedido_id}` : '<small>avulso</small>') },
    { t: 'Forma', cls: 'nowrap', v: (t) => forma(t.tipo) },
    { t: 'Detalhe', v: (t) => `<span class="mono">${esc(t.detalhes.cartao || t.detalhes.linha_digitavel || t.detalhes.copia_e_cola || t.detalhes.id)}</span>` },
    { t: 'Valor', cls: 'num', v: (t) => (t.valor == null ? '·' : brl(t.valor)) },
    { t: 'Status', v: (t) => pill(t.detalhes.status) },
    { t: '', cls: 'actions', v: (t) => (t.detalhes.status === 'pending' ? `<button class="btn small ghost" data-confirmar="${t.id}">Confirmar boleto</button>` : '') },
  ], historico, 'Nenhuma transação ainda.');
}

function sugerirForma() {
  const opt = $('#pag-pedido').selectedOptions[0];
  if (opt && opt.dataset.forma) $('#pag-forma').value = opt.dataset.forma;
  $('#pag-cartao-wrap').hidden = $('#pag-forma').value !== 'cartao_credito';
}
$('#pag-pedido').addEventListener('change', sugerirForma);
$('#pag-forma').addEventListener('change', sugerirForma);

$('#form-pagamento').addEventListener('submit', tentar(async (e) => {
  e.preventDefault();
  const body = Object.fromEntries(new FormData(e.target));
  if (!body.pedido_id) throw new Error('Crie um pedido primeiro');
  const { transacao } = await api('pagamentos', '/pagamentos', { method: 'POST', body });
  toast(transacao.detalhes.status === 'pending' ? `Boleto gerado para o pedido ${transacao.pedido_id}` : `Pedido ${transacao.pedido_id} pago`);
  e.target.cartao.value = '';
  await carregarPagamentos();
}));

$('#tabela-transacoes').addEventListener('click', tentar(async (e) => {
  const id = e.target.dataset.confirmar;
  if (!id) return;
  const { message } = await api('pagamentos', `/pagamentos/${id}/confirmar`, { method: 'POST' });
  toast(message);
  await carregarPagamentos();
}));

window.addEventListener('hashchange', navegar);
navegar();
