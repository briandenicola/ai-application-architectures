"""Regenerate the README diagrams: `python docs/diagrams/generate.py`.

Each diagram is written twice from the same drawing calls:
  <name>.svg         rendered in the README
  <name>.excalidraw  editable at excalidraw.com / VS Code Excalidraw extension
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diagram_lib import D, C, GRAY, RED, LINE  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- helpers
def lanes(d, specs, top=20, bottom=None):
    """specs: [(x_center, label, style)] -> header chips + dashed lifelines."""
    bottom = bottom or d.h - 20
    for x, label, st in specs:
        d.chip(x - 85, top, 170, 46, label, st, 13, True)
        d.arrow([(x, top + 46), (x, bottom)], head=False, color='#ced4da', dashed=True, sw=1)


def msg(d, x1, x2, y, label, ret=False, size=11):
    d.arrow([(x1, y), (x2 - 6 if x2 > x1 else x2 + 6, y)], dashed=ret,
            label=label, lx=(x1 + x2) / 2, ly=y - 11, lanchor='middle', lsize=size)


def note(d, x, y, w, h, lines, st='hl'):
    d.rect(x, y, w, h, st, sw=1)
    for i, l in enumerate(lines):
        d.text(x + w / 2, y + 16 + i * 17, l, 11)


diagrams = []

# ---------------------------------------------------------------- 1. system
d = D('01-system-architecture', 1000, 650)
# browser
d.rect(20, 40, 280, 580, 'exp'); d.text(160, 64, 'BROWSER', 15, True, C('exp'))
d.text(160, 84, 'host/public · host/src/host.ts', 11, color=GRAY)
d.chip(40, 110, 240, 40, 'Chat UI + event log', 'plain', 13, True)
d.chip(40, 180, 240, 40, 'AG-UI SSE reader', 'plain', 13, True)
d.arrow([(160, 220), (160, 306)], label='ACTIVITY_SNAPSHOT', lx=170, ly=252, lsize=11)
d.text(170, 270, '(mcp-apps)', 11, color=GRAY, anchor='start')
d.chip(40, 306, 240, 44, 'AppBridge  (client = null)', 'button', 13, True)
d.rect(36, 404, 248, 200, 'plain', dashed=True)
d.chip(56, 440, 208, 44, 'MCP App view', 'app', 14, True)
d.text(160, 506, 'wire-review.html', 12, mono=True)
d.text(160, 526, 'App · ontoolresult', 12, mono=True)
d.text(160, 546, 'callServerTool · sendMessage', 12, mono=True)
d.text(160, 588, 'SANDBOXED IFRAME · opaque origin', 11, True, GRAY)
d.arrow([(160, 350), (160, 440)], label='postMessage · ui/*', lx=170, ly=378, lsize=11)
# BFF
d.rect(380, 40, 320, 580, 'host'); d.text(540, 64, 'HOST BFF', 15, True, C('host'))
d.text(540, 84, 'host/server.ts · Node · :3000', 11, color=GRAY)
d.chip(396, 110, 112, 38, 'POST /api/run', 'plain', 12, mono=True)
d.chip(396, 309, 112, 38, 'POST /api/mcp', 'plain', 12, mono=True)
d.box(530, 110, 154, 290, 'app', 'MCPAppsMiddleware', ['', '1 list MCP tools', '2 inject as', '   client tools', '3 run pending', '   MCP calls', '4 emit mcp-apps', '5 proxy UI calls'],
      tsize=13, lsize=12, ltop=56, lstep=26)
d.arrow([(508, 129), (530, 129)])
d.arrow([(508, 328), (530, 328)])
d.arrow([(607, 400), (607, 450)], label='runNext', lx=617, ly=425, lsize=11)
d.chip(530, 450, 154, 44, 'HttpAgent', 'plain', 14, True)
d.text(540, 590, 'agent.use(middleware)', 12, mono=True, color=GRAY)
# browser -> BFF
d.arrow([(280, 129), (396, 129)], label='AG-UI · SSE', lx=338, ly=113, lanchor='middle', lsize=11)
d.arrow([(280, 328), (396, 328)], label='proxied MCP', lx=338, ly=312, lanchor='middle', lsize=11)
# MCP server
d.rect(760, 40, 220, 230, 'mcp'); d.text(870, 64, 'MCP SERVER', 15, True, C('mcp'))
d.text(870, 84, 'mcp-server/ · Node · :3001', 11, color=GRAY)
for i, (t, cap) in enumerate([('get_high_risk_wires', 'model-visible · has UI'),
                               ('create_hold_request', 'app-only'),
                               ('ui://banking/wire-review', 'UI resource (HTML)')]):
    y = 104 + i * 52
    d.chip(776, y, 188, 28, t, 'plain', 11, mono=True)
    d.text(870, y + 40, cap, 11, color=GRAY)
d.arrow([(684, 200), (760, 200)], label='MCP HTTP', lx=722, ly=184, lanchor='middle', lsize=11)
# MAF
d.rect(760, 330, 220, 200, 'harness'); d.text(870, 354, 'MAF AGENT', 15, True, C('harness'))
d.text(870, 374, 'agent/main.py · Python · :8888', 11, color=GRAY)
for i, t in enumerate(['AG-UI FastAPI endpoint', 'Agent "wire-ops"', 'chat client']):
    d.chip(780, 394 + i * 38, 180, 30, t, 'plain', 12)
d.text(870, 518, 'no MCP code', 11, True, GRAY)
d.arrow([(684, 472), (760, 472)], label='AG-UI', lx=722, ly=456, lanchor='middle', lsize=11)
# LLM
d.chip2(760, 566, 220, 54, 'LLM', 'Foundry · Azure OpenAI · fake', 'workflow')
d.arrow([(870, 530), (870, 566)])
diagrams.append(d)

# ---------------------------------------------------------------- 2. turn 1
X = [100, 300, 500, 690, 890]
d = D('02-turn1-render-the-app', 1000, 760)
lanes(d, list(zip(X, ['Browser host', 'Host BFF + middleware', 'MAF agent', 'LLM', 'MCP server'],
                  ['exp', 'host', 'harness', 'workflow', 'mcp'])))
B, H, A, L, M = X
steps = [
    (B, H, '1  POST /api/run  "show me high-risk wires"', False),
    (H, M, '2  tools/list', False),
    (M, H, '3  tools + _meta.ui.resourceUri', True),
    (H, A, '4  AG-UI run · tools += MCP tools', False),
    (A, L, '5  messages + tool schemas', False),
    (L, A, '6  tool_call get_high_risk_wires', True),
    (A, H, '7  TOOL_CALL_* … RUN_FINISHED', True),
    (H, M, '8  tools/call get_high_risk_wires', False),
    (M, H, '9  content + structuredContent', True),
    (H, B, '10  TOOL_CALL_RESULT · ACTIVITY_SNAPSHOT', True),
    (B, H, '11  POST /api/mcp  resources/read', False),
    (H, M, '12  resources/read  (MAF bypassed)', False),
    (M, B, '13  text/html;profile=mcp-app', True),
]
y = 110
for x1, x2, label, ret in steps:
    msg(d, x1, x2, y, label, ret)
    y += 44
note(d, 20, y - 6, 300, 58, ['14  iframe(srcdoc) + AppBridge.connect()',
                              'ui/initialize → tool-input → tool-result'], 'app')
note(d, 512, 344, 170, 40, ['MAF does NOT run it:', 'client tool → stays pending'])
diagrams.append(d)

# ---------------------------------------------------------------- 3. turn 2
X = [100, 300, 500, 700, 890]
d = D('03-turn2-app-calls-back', 1000, 560)
lanes(d, list(zip(X, ['MCP App view', 'Browser host', 'Host BFF + middleware', 'MAF agent', 'MCP server'],
                  ['app', 'exp', 'host', 'harness', 'mcp'])))
V, Bh, H, A, M = X
d.text(20, 96, 'A · "Create hold request" calls an app-only tool', 13, True, C('app'), anchor='start')
y = 136
for x1, x2, label, ret in [
    (V, Bh, 'tools/call create_hold_request', False),
    (Bh, H, 'POST /api/mcp (proxied)', False),
    (H, M, 'tools/call (allowlisted)', False),
    (M, V, 'HOLD-1234 · PENDING_APPROVAL', True),
]:
    msg(d, x1, x2, y, label, ret); y += 42
note(d, 610, 132, 180, 40, ['MAF never sees this call', 'model never sees this tool'])
d.arrow([(20, y), (980, y)], head=False, color='#dee2e6', sw=1)
d.text(20, y + 24, 'B · "Ask the agent" hands a turn back to the conversation', 13, True, C('app'), anchor='start')
y += 64
for x1, x2, label, ret in [
    (V, Bh, 'ui/message "Summarize TX123…"', False),
    (Bh, H, 'POST /api/run (new turn)', False),
    (H, A, 'AG-UI run (history incl. result)', False),
    (A, Bh, 'TEXT_MESSAGE_* stream', True),
]:
    msg(d, x1, x2, y, label, ret); y += 42
diagrams.append(d)

# ---------------------------------------------------------------- 4. who knows what
d = D('04-who-knows-what', 1000, 410)
cards = [
    ('MCP App view', 'app', ['postMessage (ui/*)'], ['its tool input', 'its tool result'],
     ['the network', 'the MCP server', 'the agent']),
    ('Browser host', 'exp', ['AG-UI events', 'AppBridge'], ['mcp-apps activity', 'the UI HTML'],
     ['the MCP server', '(goes via BFF)']),
    ('MCPAppsMiddleware', 'host', ['AG-UI', 'MCP'], ['tool _meta.ui', 'resourceUri', 'server hash/id'],
     ['the model', 'the iframe']),
    ('MAF agent', 'harness', ['AG-UI', 'chat API'], ['plain client-tool', 'schemas'],
     ['MCP', 'UI resources', 'tool results*']),
    ('MCP server', 'mcp', ['MCP'], ['tool calls', 'resource reads'],
     ['the model', 'the host', 'the agent']),
]
for i, (title, st, speaks, sees, never) in enumerate(cards):
    x = 20 + i * 194
    d.rect(x, 20, 182, 330, st, dashed=(i == 0))
    d.text(x + 91, 44, title, 14, True, C(st))
    yy = 76
    for head, items, col in [('SPEAKS', speaks, None), ('SEES', sees, None), ('NEVER SEES', never, RED)]:
        d.text(x + 16, yy, head, 11, True, col or GRAY, anchor='start'); yy += 22
        for it in items:
            d.text(x + 16, yy, it, 12, color=col or '#1e1e1e', anchor='start'); yy += 19
        yy += 10
d.text(500, 372, 'Dashed = trust boundary: the view is untrusted; everything it asks for is mediated by the host.', 12, color=GRAY)
d.text(500, 394, '* MAF sees tool results only on the next turn, as history.', 11, color=GRAY)
diagrams.append(d)

# ---------------------------------------------------------------- 5. taskfile
d = D('05-taskfile', 1000, 370)
d.chip(20, 150, 130, 50, 'task up:fake', 'primary', 14, True, mono=True)
d.rect(200, 30, 230, 300, 'plain'); d.text(315, 54, '1 · setup', 14, True)
for i, (t, s) in enumerate([('setup:mcp', 'npm install'), ('setup:host', 'npm install'),
                             ('setup:agent', 'venv · pip · .env')]):
    d.chip2(220, 76 + i * 78, 190, 58, t, s)
d.rect(480, 30, 230, 300, 'plain'); d.text(595, 54, '2 · build', 14, True)
d.chip2(500, 76, 190, 58, 'build:ui', 'vite → single-file HTML')
d.chip2(500, 154, 190, 58, 'build:host', 'esbuild → public/host.js')
d.text(595, 300, 'skipped when sources unchanged', 11, color=GRAY)
d.rect(760, 30, 220, 300, 'plain'); d.text(870, 54, '3 · run (parallel)', 14, True)
for i, (t, s, st) in enumerate([('run:mcp', ':3001', 'mcp'), ('run:agent', ':8888', 'harness'),
                                 ('run:host', ':3000', 'host'), ('run:fake-llm', ':8889', 'workflow')]):
    d.chip2(780, 72 + i * 62, 180, 50, t, s, st)
d.arrow([(150, 175), (200, 175)]); d.arrow([(430, 175), (480, 175)]); d.arrow([(710, 175), (760, 175)])
d.text(870, 340, 'Ctrl+C stops all · then: task verify', 11, color=GRAY)
diagrams.append(d)

# ---------------------------------------------------------------- 6. Cowork
d = D('06-cowork-architecture', 1200, 730)
d.text(600, 28, 'Microsoft Copilot Cowork: implemented Azure path', 20, True)
d.rect(20, 70, 300, 540, 'exp')
d.text(170, 96, 'MICROSOFT 365', 15, True, C('exp'))
d.box(40, 120, 260, 110, 'exp', 'Copilot Cowork',
      ['Banking skill + MCP client', 'Native MCP App host'], lsize=13)
d.box(40, 300, 260, 140, 'app', 'Wire-review panel',
      ['Same single-file HTML', 'tools/call: request a hold', 'ui/message: ask the agent'], lsize=13)
d.arrow([(170, 230), (170, 300)], label='MCP Apps bridge', lx=182, ly=265)
d.text(170, 535, 'Plugin ZIP: skill + connector', 13)
d.text(170, 560, 'Remote MCP auth: None', 13, True, RED)
d.rect(390, 70, 790, 540, 'plain')
d.text(785, 96, 'AZURE', 15, True)
d.box(410, 140, 320, 150, 'mcp', 'Gateway Function',
      ['Public HTTPS /mcp', 'Tools + UI resource', 'Managed identity: Foundry'], lsize=13)
d.box(810, 140, 340, 150, 'domain', 'Banking Function',
      ['Internal ingress only', 'Synthetic wire lookup', 'Persist pending hold requests'], lsize=13)
d.arrow([(300, 177), (410, 177)], label='MCP / HTTPS', lx=355, ly=155,
        lanchor='middle', lsize=11)
d.arrow([(730, 200), (810, 200)], label='HTTP', lx=770, ly=182,
        lanchor='middle', lsize=11)
d.box(410, 370, 320, 140, 'harness', 'Foundry prompt agent',
      ['Gateway calls Responses API', 'Selected wire + question', 'Text advice; no banking tools'], lsize=13)
d.arrow([(570, 290), (570, 370)], label='analyze_wire / Entra token', lx=582, ly=333, lsize=11)
d.box(810, 370, 340, 140, 'workflow', 'Private banking storage',
      ['hold-requests/*.json', 'PENDING_APPROVAL', 'Banking managed identity'], lsize=13)
d.arrow([(980, 290), (980, 370)], label='Blob private endpoint', lx=992, ly=333, lsize=11)
d.text(785, 550, 'Both Functions: one ACR image, separate identities and host storage', 13)
d.text(785, 577, 'Container Apps environment + VNet + private Blob / Queue / Table DNS', 12, color=GRAY)
d.text(600, 646, 'Read: tool data + UI URI -> native panel (no Foundry call)', 14)
d.text(600, 674, 'Investigate: panel message -> Cowork -> analyze_wire -> Foundry', 14)
d.text(600, 702, 'Request: panel -> app-only tool -> persist before success; no approval or execution', 14, True)
diagrams.append(d)

for d in diagrams:
    d.save(OUT)
print(f'{len(diagrams)} diagrams written to {OUT}')
