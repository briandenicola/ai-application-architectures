/**
 * The View: runs inside the host's sandboxed iframe.
 *
 * It never talks to the MCP server directly. Everything goes over postMessage
 * to the host (AppBridge), and the host decides whether and how to forward it:
 *   ontoolresult      host pushes the get_high_risk_wires result in
 *   callServerTool()  UI asks the host to call create_hold_request
 *   sendMessage()     UI asks the host to post a chat message to the agent
 */
import { App } from "@modelcontextprotocol/ext-apps";

type Wire = {
  id: string; customer: string; amount: number; currency: string;
  destination: string; risk: number; signals: string[];
};

const $ = (id: string) => document.getElementById(id)!;
const fmt = (n: number) => `$${(n / 1e6).toFixed(1)}M`;
let selected: Wire | null = null;

const app = new App({ name: "Wire Review", version: "1.0.0" });

// Set handlers BEFORE connect() so the initial result isn't missed.
app.ontoolresult = (result) => {
  const data = result.structuredContent as { minRisk: number; wires: Wire[] } | undefined;
  render(data?.wires ?? [], data?.minRisk);
};

function render(wires: Wire[], minRisk?: number) {
  $("meta").textContent = `${wires.length} wire(s) · risk ≥ ${minRisk ?? "?"}`;
  const tbody = $("rows");
  tbody.innerHTML = "";
  if (!wires.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty">No wires above threshold.</td></tr>`;
    return;
  }
  for (const w of wires) {
    const tr = document.createElement("tr");
    tr.className = "wire";
    tr.innerHTML = `<td class="mono">${w.id}</td><td>${w.customer}</td><td>${fmt(w.amount)}</td><td class="risk">${w.risk}</td>`;
    tr.onclick = () => select(w, tr);
    tbody.appendChild(tr);
  }
}

function select(w: Wire, tr: HTMLElement) {
  selected = w;
  document.querySelectorAll("tr.wire").forEach((r) => r.classList.remove("selected"));
  tr.classList.add("selected");
  $("detail").classList.add("open");
  $("detail-title").textContent = `${w.id} · ${w.customer} · ${fmt(w.amount)} → ${w.destination}`;
  $("signals").innerHTML = w.signals.map((s) => `<li>${s}</li>`).join("") || "<li>No signals</li>";
  $("status").textContent = "";
  $("status").className = "status";
  ($("hold") as HTMLButtonElement).disabled = false;
}

// UI → host → MCP server (app-only tool). The UI only expresses intent.
$("hold").addEventListener("click", async () => {
  if (!selected) return;
  const btn = $("hold") as HTMLButtonElement;
  btn.disabled = true;
  $("status").textContent = "Submitting…";
  try {
    const res = await app.callServerTool({
      name: "create_hold_request",
      arguments: { wireId: selected.id, reason: "Flagged in MCP App review" },
    });
    if (res.isError) throw new Error(res.content?.find((c) => c.type === "text")?.text ?? "Tool error");
    const hold = res.structuredContent as { holdRequestId: string; status: string };
    $("status").textContent = `✓ ${hold.holdRequestId} — ${hold.status}`;
    $("status").className = "status ok";
  } catch (e) {
    $("status").textContent = `✗ ${(e as Error).message}`;
    $("status").className = "status err";
    btn.disabled = false;
  }
});

// UI → host → agent: hand a follow-up turn back to the conversation.
$("ask").addEventListener("click", async () => {
  if (!selected) return;
  await app.sendMessage({
    role: "user",
    content: [{ type: "text", text: `Summarize the risk signals on wire ${selected.id} and recommend next steps.` }],
  });
});

app.connect();
