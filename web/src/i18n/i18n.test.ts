import { describe, expect, it } from 'vitest';
import { catalog, getLang, msg, setLang } from '.';
import { fmt, fmtPct, parseNumber, toInput } from '../lib/format';

type Tree = { [k: string]: unknown };

/** Rutas de hojas (texto o función) de un catálogo, con la aridad de las funciones. */
function leaves(node: unknown, path = ''): Map<string, string> {
  const out = new Map<string, string>();
  if (typeof node === 'string') out.set(path, 'string');
  else if (typeof node === 'function') out.set(path, `fn/${node.length}`);
  else if (Array.isArray(node))
    node.forEach((v, i) => leaves(v, `${path}[${i}]`).forEach((t, k) => out.set(k, t)));
  else if (node && typeof node === 'object')
    for (const [k, v] of Object.entries(node as Tree))
      leaves(v, path ? `${path}.${k}` : k).forEach((t, kk) => out.set(kk, t));
  return out;
}

describe('catálogos', () => {
  it('el inglés tiene exactamente las claves del español', () => {
    const es = leaves(catalog('es'));
    const en = leaves(catalog('en'));
    expect([...en.keys()].sort()).toEqual([...es.keys()].sort());
    for (const [k, kind] of es) expect(en.get(k), k).toBe(kind);
  });

  it('ningún texto queda vacío', () => {
    for (const lang of ['es', 'en'] as const)
      for (const [k] of leaves(catalog(lang))) {
        const v = k
          .split(/\.|\[|\]/)
          .filter(Boolean)
          .reduce<unknown>((o, p) => (o as Tree)[p], catalog(lang));
        if (typeof v === 'string') expect(v.trim(), `${lang}:${k}`).not.toBe('');
      }
  });
});

describe('idioma activo', () => {
  it('cambia el catálogo, el atributo lang y el formato de números', () => {
    expect(getLang()).toBe('es');
    expect(fmt(1234.5)).toBe('1.234,5');
    setLang('en');
    expect(document.documentElement.lang).toBe('en');
    expect(msg().common.yes).toBe('Yes');
    expect(fmt(1234.5)).toBe('1,234.5');
    expect(fmtPct(12.34)).toBe('+12.3%');
    expect(toInput(1.5)).toBe('1.5');
    setLang('es');
    expect(fmtPct(12.34)).toBe('+12,3 %');
    expect(toInput(1.5)).toBe('1,5');
  });

  it('lee números con miles en los dos idiomas', () => {
    expect(parseNumber('1.234,5')).toBe(1234.5);
    expect(parseNumber('1,234.5')).toBe(1234.5);
    expect(parseNumber('1,5')).toBe(1.5);
    expect(parseNumber('1.5')).toBe(1.5);
  });
});
