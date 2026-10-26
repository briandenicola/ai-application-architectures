/**
 * Browser half of the host: a tiny chat UI that consumes AG-UI events and
 * renders MCP Apps.
 *
 * In production, CopilotKit's <CopilotChat> does all of this for you. It's
 * spelled out here so every hop is visible:
 *
 *   ACTIVITY_SNAPSHOT(mcp-apps)
 *     → resources/read (via /api/mcp)        fetch the HTML for resourceUri
 *     → <iframe sandbox srcdoc=html>         untrusted UI, opaque origin
 *     → AppBridge ⇄ PostMessageTransport     MCP-style JSON-RPC over postMessage
 *     → sendToolInput / sendToolResult       hand the view its data
 *     ← oncalltool / onmessage               view asks host to act
 */
import { AppBridge, PostMessageTransport } from "@modelcontextprotocol/ext-apps/app-bridge";

type AGUIEvent = { type: string; [k: string]: any };
type McpAppsActivity = {
  resourceUri: string;
  result: any;
  toolInput: Record<string, unknown>;
  serverHash: string;
  serverId?: string;
};

const threadId = crypto.randomUUID();
let history: any[] = [];
let busy = false;

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const chat = $("chat");
const log = $("log");

// ---------- event log (right-hand panel) ----------
function logEvent(e: AGUIEvent) {
  // Collapse streamed text deltas into a single row so the log stays readable.
  const last = log.lastElementChild as HTMLElement | null;
  if (e.type === "TEXT_MESSAGE_CONTENT" && last && last.dataset.msg === e.messageId) {
    const n = Number(last.dataset.n) + 1;
    last.dataset.n = String(n);
    last.querySelector("b")!.textContent = `TEXT_MESSAGE_CONTENT ×${n}`;
    last.querySelector("span")!.textContent += e.delta;
    return;
  }
  const row = document.createElement("div");
  if (e.type === "TEXT_MESSAGE_CONTENT") { row.dataset.msg = e.messageId; row.dataset.n = "1"; }
  row.className = `ev ev-${e.type}`;
  const detail =
    e.type === "TOOL_CALL_START" ? e.toolCallName :
    e.type === "TOOL_CALL_ARGS" ? e.delta :
    e.type === "ACTIVITY_SNAPSHOT" ? `${e.activityType} → ${e.content?.resourceUri}` :
    e.type === "TOOL_CALL_RESULT" ? String(e.content).slice(0, 80) + "…" :
    e.type === "TEXT_MESSAGE_CONTENT" ? e.delta : "";
  row.innerHTML = `<b>${e.type}</b> <span>${escapeHtml(detail ?? "")}</span>`;
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
}
function logNote(text: string) {
  const row = document.createElement("div");
  row.className = "ev ev-note";
  row.textContent = text;
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
}
const escapeHtml = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));

// ---------- chat rendering ----------
function bubble(role: "user" | "assistant", text = "") {
  const el = document.createElement("div");
  el.className = `msg ${role}`;
  el.textContent = text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
  return el;
}
function chip(text: string) {
  const el = document.createElement("div");
  el.className = "chip";
  el.textContent = text;
  chat.appendChild(el);
  return el;
}

// ---------- AG-UI over SSE ----------
async function runTurn(userText: string) {
  if (busy) return;
  busy = true;
  $<HTMLButtonElement>("send").disabled = true;
  bubble("user", userText);
  history.push({ id: crypto.randomUUID(), role: "user", content: userText });

  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ threadId, messages: history }),
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  const texts = new Map<string, HTMLElement>();

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i: number;
    while ((i = buf.indexOf("\n\n")) >= 0) {
      const frame = buf.slice(0, i);
      buf = buf.slice(i + 2);
      const data = frame.split("\n").filter((l) => l.startsWith("data: ")).map((l) => l.slice(6)).join("");
      if (!data) continue;
      const e: AGUIEvent = JSON.parse(data);
      if (e.type === "HOST_MESSAGES") { history = e.messages; continue; }
      logEvent(e);
      switch (e.type) {
        case "TEXT_MESSAGE_CONTENT": {
          let el = texts.get(e.messageId);
          if (!el) { el = bubble("assistant"); texts.set(e.messageId, el); }
          el.textContent += e.delta;
          break;
        }
        case "TOOL_CALL_START":
          chip(`🔧 model called ${e.toolCallName}`);
          break;
        case "ACTIVITY_SNAPSHOT":
          if (e.activityType === "mcp-apps") await mountMcpApp(e.content as McpAppsActivity);
          break;
        case "RUN_ERROR":
          chip(`⚠ ${e.message}`);
          break;
      }
    }
  }
  busy = false;
  $<HTMLButtonElement>("send").disabled = false;
}

// ---------- MCP calls proxied through the BFF → middleware ----------
async function mcp(activity: McpAppsActivity, method: string, params: unknown) {
  logNote(`iframe → host → MCP  ${method} ${method === "tools/call" ? (params as any).name : (params as any).uri}`);
  const r = await fetch("/api/mcp", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ serverId: activity.serverId, serverHash: activity.serverHash, method, params }),
  });
  const json = await r.json();
  if (json?.error) throw new Error(json.error);
  return json;
}

// ---------- render one MCP App ----------
async function mountMcpApp(activity: McpAppsActivity) {
  // 1. Fetch the UI template the tool's _meta.ui.resourceUri pointed at.
  const resource = await mcp(activity, "resources/read", { uri: activity.resourceUri });
  const html: string = resource.contents?.[0]?.text;
  if (!html) { chip(`⚠ empty UI resource ${activity.resourceUri}`); return; }

  // 2. Sandboxed iframe. No allow-same-origin, so the view gets an opaque origin
  //    and can reach the page only through postMessage.
  const frame = document.createElement("iframe");
  frame.className = "mcp-app";
  frame.setAttribute("sandbox", "allow-scripts allow-forms");
  frame.title = activity.resourceUri;
  chat.appendChild(frame);

  // 3. The bridge. client=null: there is no direct MCP client in the browser,
  //    so every request from the view goes through our handlers to the BFF.
  const bridge = new AppBridge(
    null,
    { name: "maf-ag-ui-sample-host", version: "1.0.0" },
    { serverTools: {}, serverResources: {}, message: { text: {} }, logging: {} },
    { hostContext: { theme: "light", platform: "web", displayMode: "inline" } },
  );
  bridge.oncalltool = (params) => mcp(activity, "tools/call", params);
  bridge.onreadresource = (params) => mcp(activity, "resources/read", params);
  bridge.onmessage = async (params) => {
    const text = params.content.map((c: any) => c.text ?? "").join(" ");
    logNote(`iframe → host  ui/message: "${text}"`);
    setTimeout(() => runTurn(text), 0); // the view asks for a new chat turn
    return {};
  };
  bridge.onloggingmessage = (p) => console.log("[mcp-app]", p);
  bridge.onsizechange = ({ height }) => { if (height) frame.style.height = `${height + 4}px`; };

  const initialized = new Promise<void>((resolve) => { bridge.oninitialized = () => resolve(); });
  await bridge.connect(new PostMessageTransport(frame.contentWindow!, frame.contentWindow!));
  frame.srcdoc = html;
  await initialized;
  logNote("host ⇄ iframe  ui/initialize complete");

  // 4. Push the data in. The view renders it.
  await bridge.sendToolInput({ arguments: activity.toolInput });
  await bridge.sendToolResult(activity.result);
  chat.scrollTop = chat.scrollHeight;
}

// ---------- wiring ----------
$("form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const input = $<HTMLInputElement>("input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  runTurn(text);
});
document.querySelectorAll<HTMLButtonElement>("[data-prompt]").forEach((b) =>
  b.addEventListener("click", () => runTurn(b.dataset.prompt!)),
);
