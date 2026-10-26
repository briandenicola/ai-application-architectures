"""Tiny SVG + Excalidraw diagram helper (one source, two outputs)."""
import json, random, os
from xml.sax.saxutils import escape

random.seed(42)
S = {
    'exp': ('#364fc7', '#dbe4ff'),
    'harness': ('#6741d9', '#e5dbff'),
    'mcp': ('#0b7285', '#c5f6fa'),
    'app': ('#087f5b', '#e6fcf5'),
    'control': ('#d9480f', '#ffe8cc'),
    'domain': ('#e67700', '#fff9db'),
    'workflow': ('#1864ab', '#d0ebff'),
    'core': ('#c92a2a', '#ffe3e3'),
    'host': ('#495057', '#f1f3f5'),
    'plain': ('#868e96', '#ffffff'),
    'button': ('#1971c2', '#e7f5ff'),
    'primary': ('#1864ab', '#1c7ed6'),
    'ok': ('#2b8a3e', '#d3f9d8'),
    'bad': ('#c92a2a', '#fff5f5'),
    'thumb': ('#adb5bd', '#e9ecef'),
    'hl': ('#ffc9c9', '#fff5f5'),
}
INK = '#1e1e1e'; GRAY = '#868e96'; RED = '#c92a2a'; GREEN = '#2b8a3e'; LINE = '#495057'; FAINT = '#dee2e6'
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'Cascadia Code', Consolas, Menlo, monospace"


def tw(t, size, bold=False, mono=False):
    return len(t) * size * (0.62 if mono else (0.6 if bold else 0.55))


def r1(v):
    return round(v, 1)


class D:
    def __init__(s, name, w, h):
        s.name, s.w, s.h = name, w, h
        s.svg, s.ex = [], []

    def _id(s):
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=20))

    def _e(s, typ, x, y, w, h, stroke, bg, sw=2, dashed=False, rounded=True, **kw):
        e = dict(id=s._id(), type=typ, x=r1(x), y=r1(y), width=r1(w), height=r1(h), angle=0,
                 strokeColor=stroke, backgroundColor=bg, fillStyle='solid', strokeWidth=sw,
                 strokeStyle='dashed' if dashed else 'solid', roughness=0, opacity=100,
                 groupIds=[], frameId=None, roundness=({'type': 3} if rounded else None),
                 seed=random.randint(1, 2**31 - 1), version=1,
                 versionNonce=random.randint(1, 2**31 - 1), isDeleted=False,
                 boundElements=[], updated=1, link=None, locked=False)
        e.update(kw)
        s.ex.append(e)

    def rect(s, x, y, w, h, st='plain', dashed=False, sw=2, rounded=True):
        stroke, bg = S[st]
        s._e('rectangle', x, y, w, h, stroke, bg, sw=sw, dashed=dashed, rounded=rounded)
        da = ' stroke-dasharray="8 6"' if dashed else ''
        s.svg.append(f'<rect x="{r1(x)}" y="{r1(y)}" width="{r1(w)}" height="{r1(h)}" rx="{8 if rounded else 0}" '
                     f'fill="{bg}" stroke="{stroke}" stroke-width="{sw}"{da}/>')

    def ellipse(s, cx, cy, r, st='plain', label=None, size=13):
        stroke, bg = S[st]
        s._e('ellipse', cx - r, cy - r, 2 * r, 2 * r, stroke, bg, sw=2, rounded=False)
        s.svg.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{bg}" stroke="{stroke}" stroke-width="2"/>')
        if label:
            s.text(cx, cy, label, size, True)

    def text(s, x, y, t, size=14, bold=False, color=INK, anchor='middle', mono=False, halo=False):
        w = tw(t, size, bold, mono); h = size * 1.25
        ex_x = x - w / 2 if anchor == 'middle' else (x - w if anchor == 'end' else x)
        s._e('text', ex_x, y - h / 2, w, h, color, 'transparent', sw=1, rounded=False,
             text=t, fontSize=size, fontFamily=3 if mono else 2,
             textAlign={'middle': 'center', 'start': 'left', 'end': 'right'}[anchor],
             verticalAlign='top', containerId=None, originalText=t, autoResize=True, lineHeight=1.25)
        fam = MONO if mono else FONT
        extra = ' xml:space="preserve"'
        if halo:
            s.svg.append(f'<rect x="{r1(ex_x-4)}" y="{r1(y-h/2)}" width="{r1(w+8)}" height="{r1(h)}" fill="#ffffff"/>')
            s._e('rectangle', ex_x - 4, y - h / 2, w + 8, h, '#ffffff', '#ffffff', sw=1, rounded=False)
            s.ex.append(s.ex.pop(-2))  # keep text above its backing rect
        s.svg.append(f'<text x="{r1(x)}" y="{r1(y)}" font-family="{fam}" font-size="{size}" '
                     f'font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}" '
                     f'dominant-baseline="central"{extra}>{escape(t)}</text>')

    def arrow(s, pts, head=True, color=LINE, dashed=False, label=None, lx=None, ly=None,
              lanchor='start', lsize=12, sw=2):
        x0, y0 = pts[0]
        rel = [[px - x0, py - y0] for px, py in pts]
        xs = [p[0] for p in rel]; ys = [p[1] for p in rel]
        s._e('arrow' if head else 'line', x0, y0, max(xs) - min(xs), max(ys) - min(ys), color,
             'transparent', sw=sw, dashed=dashed, rounded=False, points=rel,
             lastCommittedPoint=None, startBinding=None, endBinding=None,
             startArrowhead=None, endArrowhead='arrow' if head else None)
        p = ' '.join(f'{r1(a)},{r1(b)}' for a, b in pts)
        m = f' marker-end="url(#ah{"r" if color == RED else ""})"' if head else ''
        da = ' stroke-dasharray="8 6"' if dashed else ''
        s.svg.append(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{sw}" '
                     f'stroke-linejoin="round"{da}{m}/>')
        if label:
            s.text(lx, ly, label, lsize, color=GRAY if color != RED else RED, anchor=lanchor, halo=True)

    def box(s, x, y, w, h, st, title=None, lines=(), tsize=15, lsize=13, mono=False, dashed=False,
            ltop=None, lstep=20):
        s.rect(x, y, w, h, st, dashed=dashed)
        if title:
            s.text(x + w / 2, y + 24, title, tsize, True, S[st][0])
        n = len(lines)
        yy = y + (ltop if ltop else (52 if title else h / 2 - (n - 1) * lstep / 2))
        for i, l in enumerate(lines):
            s.text(x + w / 2, yy + i * lstep, l, lsize, mono=mono)

    def chip(s, x, y, w, h, label, st='plain', size=13, bold=False, mono=False, color=None):
        s.rect(x, y, w, h, st, sw=1)
        c = color or ('#ffffff' if st == 'primary' else INK)
        s.text(x + w / 2, y + h / 2, label, size, bold, c, mono=mono)

    def chip2(s, x, y, w, h, label, sub, st='plain'):
        s.rect(x, y, w, h, st, sw=1)
        s.text(x + w / 2, y + h / 2 - 9, label, 14, True)
        s.text(x + w / 2, y + h / 2 + 11, sub, 12, color=GRAY)

    def chips(s, cx, y, labels, st='plain', h=28, gap=10, size=13, pad=14, bold=False, styles=None, mono=False):
        ws = [tw(l, size, bold, mono) + 2 * pad for l in labels]
        total = sum(ws) + gap * (len(ws) - 1)
        x = cx - total / 2
        for i, (l, w) in enumerate(zip(labels, ws)):
            s.chip(x, y, w, h, l, styles[i] if styles else st, size, bold, mono)
            x += w + gap

    def save(s, out):
        defs = ('<defs>'
                '<marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker>'
                '<marker id="ahr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s.w} {s.h}" width="{s.w}" height="{s.h}">'
               + defs + '<rect width="100%" height="100%" fill="#ffffff"/>' + '\n'.join(s.svg) + '</svg>')
        with open(os.path.join(out, s.name + '.svg'), 'w') as f:
            f.write(svg)
        ex = {'type': 'excalidraw', 'version': 2, 'source': 'https://excalidraw.com', 'elements': s.ex,
              'appState': {'viewBackgroundColor': '#ffffff', 'gridSize': None}, 'files': {}}
        with open(os.path.join(out, s.name + '.excalidraw'), 'w') as f:
            json.dump(ex, f, indent=1)


def C(st):
    return S[st][0]


