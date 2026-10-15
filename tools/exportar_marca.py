"""Exporta la marca SVG con tipografía convertida a curvas (requiere fonttools y brotli)."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / 'static/img'
OUT = ROOT / 'exports/marca'
OUT.mkdir(parents=True, exist_ok=True)
icon = (IMG / 'logo.svg').read_text(encoding='utf-8')
art = icon[icon.index('  <path'):icon.index('</svg>')]
sello = icon.replace('  <path', '  <rect width="256" height="256" rx="32" fill="#0a0b0d"/>\n  <path', 1)
(IMG / 'logo-sello.svg').write_text(sello, encoding='utf-8')

def texto(t, fontfile, x, y, size, fill):
    font = TTFont(ROOT / 'static/vendor/fonts' / fontfile)
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / font['head'].unitsPerEm
    paths = []
    for c in t:
        name = cmap[ord(c)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        paths.append(f'<path transform="translate({x:.3f} {y}) scale({scale:.6f} {-scale:.6f})" fill="{fill}" d="{pen.getCommands()}"/>')
        x += glyphs[name].width * scale
    return '\n'.join(paths), x

white, end = texto('GARAJE', 'saira-condensed-800.woff2', 288, 150, 112, '#fff')
red, end = texto('DATA', 'saira-condensed-800.woff2', end, 150, 112, '#e3262b')
sub, _ = texto('BITÁCORA DEL AUTOMÓVIL', 'inter-500.woff2', 290, 195, 20, '#adb5c0')
full = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {end+30:.0f} 256" role="img" aria-label="GarajeData · Bitácora del automotor">\n{art}\n{white}\n{red}\n{sub}\n</svg>'
(IMG / 'logo-completo.svg').write_text(full, encoding='utf-8')
for filename in ['logo.svg','logo-sello.svg','logo-completo.svg']:
    (OUT / ('garajedata-' + filename)).write_bytes((IMG / filename).read_bytes())
print('SVG exportados con letras en curvas; fondo transparente y sello oscuro.')
