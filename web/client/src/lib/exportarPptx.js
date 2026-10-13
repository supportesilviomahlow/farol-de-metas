// Botão "Exportar PowerPoint": gera o slide igual ao do Call Nacional, para o RH colar na
// apresentação. Lideranças = slide 33 (duas colunas); diretoria = slide 36 (linhas grandes com
// área e barra). Formas e textos nativos (editáveis), Calibri, nas posições medidas no slide
// original exportado em 1920x1080 - por isso as medidas abaixo estão em px dessa imagem.
// Sem o multiplicador: o pedido foi "igual ao slide" (12/10/2026).
import { MES_NOME } from './ranking.js';

const COR = {
  laranja: 'EC6608', preto: '1C1C1B', cinzaTexto: '575756', cinza: '8A8A89', cinzaClaro: '9D9D9C',
  bronze: 'B87333', bronzeBarra: 'C8793A', borda: 'DEDEDD', faixa: 'F2F1EF', zebra: 'F7F7F6',
  chip: 'FDF0E6', trilho: 'E4E4E3', branco: 'FFFFFF', vermelho: 'C0392B',
};
const PX = 144; // 1920 px = 13,333 pol (LAYOUT_WIDE)
const caixa = (x, y, w, h) => ({ x: x / PX, y: y / PX, w: w / PX, h: h / PX });
const pct = (x, casas = 0) => (x == null ? '–'
  : `${(x * 100).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas, useGrouping: false })}%`);

function retangulo(pptx, s, x, y, w, h, cor, borda) {
  s.addShape(pptx.ShapeType.rect, {
    ...caixa(x, y, w, h), fill: { color: cor },
    line: borda ? { color: borda, width: 0.75 } : { type: 'none' },
  });
}

function texto(s, t, x, y, w, h, o = {}) {
  s.addText(Array.isArray(t) ? t : String(t), {
    ...caixa(x, y, w, h), fontFace: 'Calibri', fontSize: 12, color: COR.preto, margin: 0,
    valign: 'middle', align: 'left', fit: 'none', ...o,
  });
}

function cabecalho(pptx, s, titulo, geral, alturaFaixa) {
  retangulo(pptx, s, 18, 0, 1902, alturaFaixa, COR.preto);
  retangulo(pptx, s, 0, 0, 18, 1080, COR.laranja);
  texto(s, titulo, 52, 8, 1100, 124, { fontSize: 44, bold: true, color: COR.branco });
  retangulo(pptx, s, 1458, 18, 425, 102, COR.laranja);
  texto(s, `GERAL  ${pct(geral, 1)}`, 1458, 18, 425, 102, { fontSize: 24, bold: true, color: COR.branco, align: 'center' });
}

/** Nome em maiúsculas; quem não preencheu o farol ganha "NÃO PREENCHEU" em vermelho ao lado. */
function nomeComAviso(x, negrito, tamanhoAviso = 9) {
  const nome = x.pessoa.nome.toUpperCase();
  if (!x.semFarol) return nome;
  return [
    { text: nome, options: { bold: negrito } },
    { text: '   NÃO PREENCHEU', options: { bold: true, color: COR.vermelho, fontSize: tamanhoAviso } },
  ];
}

// ------------------------------------------------------------------ slide 33 (lideranças)
function colunaLiderancas(pptx, s, itens, dx) {
  const y0 = 187;
  const alt = 35.72; // 25 linhas até o pé do slide
  const rotulo = { fontSize: 12, bold: true, color: COR.cinzaTexto, charSpacing: 1.4 };
  texto(s, '#', dx + 20, 145, 72, 42, { ...rotulo, align: 'center' });
  texto(s, 'LIDERANÇA', dx + 114, 145, 500, 42, rotulo);
  texto(s, '%', dx + 652, 145, 120, 42, { ...rotulo, align: 'center' });
  texto(s, 'DESEMPATE', dx + 700, 145, 210, 42, { ...rotulo, align: 'right' });
  itens.forEach((x, i) => {
    const y = y0 + i * alt;
    retangulo(pptx, s, dx + 20, y, 886, alt, i % 2 ? COR.zebra : COR.branco);
    retangulo(pptx, s, dx + 20, y + alt - 1, 886, 1, COR.borda);
    if (x.pos <= 3) {
      const cor = [COR.laranja, COR.cinza, COR.bronze][x.pos - 1];
      s.addShape(pptx.ShapeType.ellipse, { ...caixa(dx + 26, y + 7, 22, 22), fill: { color: cor }, line: { type: 'none' } });
      texto(s, x.pos, dx + 26, y + 7, 22, 22, { fontSize: 10, bold: true, color: COR.branco, align: 'center' });
    } else {
      texto(s, x.pos, dx + 20, y, 72, alt, { color: COR.cinza, align: 'center' });
    }
    texto(s, nomeComAviso(x, x.pos <= 3), dx + 114, y, 540, alt, { bold: x.pos <= 3 });
    const alto = !x.semFarol && x.pct >= 0.855;
    texto(s, x.semFarol ? 'N/A' : pct(x.pct), dx + 652, y, 120, alt,
      { bold: true, align: 'center', color: x.semFarol ? COR.vermelho : alto ? COR.laranja : COR.cinzaTexto });
    texto(s, x.semFarol ? 'N/A' : pct(x.des, 1), dx + 740, y, 160, alt, { color: COR.cinzaClaro, align: 'right' });
  });
  return y0 + itens.length * alt;
}

function slideLiderancas(pptx, titulo, geral, lista) {
  const s = pptx.addSlide();
  s.background = { color: COR.branco };
  cabecalho(pptx, s, titulo, geral, 138);
  retangulo(pptx, s, 18, 143, 1902, 44, COR.faixa);         // faixa dos rótulos
  retangulo(pptx, s, 914, 143, 14, 937, COR.faixa);          // separador entre as colunas
  const meio = Math.min(25, Math.ceil(lista.length / 2) + 2); // o slide usa 25 + 20
  colunaLiderancas(pptx, s, lista.slice(0, meio), 0);
  const fim = colunaLiderancas(pptx, s, lista.slice(meio), 937);
  retangulo(pptx, s, 957, fim, 886, 35.72, COR.branco, COR.borda); // linha vazia do fim, como no slide
}

// ------------------------------------------------------------------ slide 36 (diretoria)
function slideDiretoria(pptx, titulo, geral, lista) {
  const s = pptx.addSlide();
  s.background = { color: COR.branco };
  cabecalho(pptx, s, titulo, geral, 158);
  const rotulo = { fontSize: 12, bold: true, color: COR.cinzaTexto, charSpacing: 1.4 };
  retangulo(pptx, s, 18, 339, 1902, 63, COR.faixa);
  texto(s, '#', 50, 339, 78, 63, { ...rotulo, align: 'center' });
  texto(s, 'LIDERANÇA', 168, 339, 500, 63, rotulo);
  texto(s, 'ÁREA', 850, 339, 300, 63, rotulo);
  texto(s, '%', 1220, 339, 160, 63, { ...rotulo, align: 'center' });
  texto(s, 'DESEMPATE', 1405, 339, 190, 63, rotulo);
  texto(s, 'BARRA', 1608, 339, 200, 63, rotulo);

  const alt = 138;
  lista.forEach((x, i) => {
    const y = 402 + i * alt;
    retangulo(pptx, s, 20, y, 1900, alt, i % 2 ? COR.zebra : COR.branco);
    retangulo(pptx, s, 20, y + alt - 1, 1900, 1, COR.borda);
    const corPos = [COR.laranja, COR.cinza, COR.bronzeBarra][x.pos - 1];
    if (corPos) retangulo(pptx, s, 18, y + 10, 14, alt - 20, corPos);
    texto(s, x.pos, 50, y, 78, alt, { fontSize: 28, bold: true, align: 'center', color: corPos || COR.cinzaClaro });
    texto(s, nomeComAviso(x, true, 11), 168, y + 22, 640, 56, { fontSize: 18, bold: true });
    texto(s, x.pessoa.area || '', 168, y + 78, 640, 40, { fontSize: 12, color: COR.cinzaClaro });
    s.addShape(pptx.ShapeType.roundRect, {
      ...caixa(835, y + 38, 356, 62), rectRadius: 0.06, fill: { color: COR.chip }, line: { color: COR.laranja, width: 0.75 },
    });
    texto(s, x.pessoa.area || '', 835, y + 38, 356, 62, { fontSize: 11, bold: true, color: COR.laranja, align: 'center' });
    const cheio = !x.semFarol && x.pct >= 0.995;
    texto(s, x.semFarol ? 'N/A' : pct(x.pct), 1220, y, 160, alt,
      { fontSize: 28, bold: true, align: 'center', color: x.semFarol ? COR.vermelho : cheio ? COR.laranja : COR.cinzaTexto });
    texto(s, x.semFarol ? 'N/A' : pct(x.des, 1), 1405, y, 150, alt, { fontSize: 15, color: COR.cinzaTexto, align: 'center' });
    retangulo(pptx, s, 1593, y + 57, 290, 32, COR.trilho);
    if (x.pct) retangulo(pptx, s, 1593, y + 57, Math.max(1, Math.min(1, x.pct) * 290), 32, x.pos === 1 ? COR.laranja : COR.bronzeBarra);
    texto(s, x.semFarol ? 'N/A' : pct(x.pct), 1700, y + 100, 166, 28, { fontSize: 10, color: COR.cinzaClaro, align: 'right' });
  });
}

/**
 * Gera e baixa o .pptx. `base` = 'ytd' ou um mês; `lista` = o ranking já montado (montarRanking).
 */
export async function exportarPptx({ grupo, base, geral, lista }) {
  const { default: PptxGenJS } = await import('pptxgenjs');
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.title = 'Farol de Metas';
  const titulo = base === 'ytd' ? 'YTD' : MES_NOME[base];
  if (grupo === 'diretoria') slideDiretoria(pptx, titulo, geral, lista);
  else slideLiderancas(pptx, titulo, geral, lista);
  const nome = grupo === 'diretoria' ? 'Ranking diretoria' : 'Ranking liderancas';
  await pptx.writeFile({ fileName: `Farol de Metas - ${nome} - ${titulo}.pptx` });
}
