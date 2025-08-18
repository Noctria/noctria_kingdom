// null/undefined/NaN/Infinity をよしなに処理する共通関数群

export const isNum = (v) => typeof v === "number" && Number.isFinite(v);

export function fmtInt(v, { dash = "−" } = {}) {
  if (isNum(v)) return Math.trunc(v).toLocaleString();
  const n = Number(v);
  return Number.isFinite(n) ? Math.trunc(n).toLocaleString() : dash;
}

export function fmtFloat(v, { digits = 2, dash = "−" } = {}) {
  if (isNum(v)) return v.toLocaleString(undefined, { maximumFractionDigits: digits });
  const n = Number(v);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: digits }) : dash;
}

export function fmtPct(v, { digits = 1, dash = "−" } = {}) {
  // v は 0〜1 を想定（0.456 -> "45.6%"）。null/NaN は dash。
  if (isNum(v)) return (v * 100).toFixed(digits) + "%";
  const n = Number(v);
  return Number.isFinite(n) ? (n * 100).toFixed(digits) + "%" : dash;
}

export function orDash(v, dash = "−") {
  // 文字列/数値をそのまま見せたい時のフォールバック
  if (v === null || v === undefined) return dash;
  if (typeof v === "number" && !Number.isFinite(v)) return dash;
  return String(v);
}

export function safeRatio(numer, denom, { digits = 1, dash = "−" } = {}) {
  // 0除算・NaN を吸収してパーセントで表示
  const n = Number(numer);
  const d = Number(denom);
  if (!Number.isFinite(n) || !Number.isFinite(d) || d <= 0) return dash;
  return ((n / d) * 100).toFixed(digits) + "%";
}

// Chart.js など “欠損値は null” にしたい時
export function toChartNumber(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

// オブジェクトから安全に取り出す（optional chaining + デフォルト）
export function pick(obj, path, defVal = null) {
  try {
    return path.split(".").reduce((o, k) => (o == null ? undefined : o[k]), obj) ?? defVal;
  } catch { return defVal; }
}
