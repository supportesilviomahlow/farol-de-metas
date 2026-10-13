// Formatação pt-BR.

export function pct(x, casas = 0) {
  if (x == null || Number.isNaN(x)) return '–';
  return `${(x * 100).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas, useGrouping: false })}%`;
}

export function mult(m) {
  return `${m.toLocaleString('pt-BR', { minimumFractionDigits: m === 0.25 ? 2 : 1 })}x`;
}
