---
name: wire-review
description: Review synthetic high-risk banking wires in an interactive panel, investigate their risk signals with an Azure Foundry agent, and request a hold for human approval.
---

# Banking wire review

Use the banking connector, not workspace files or invented results.

1. For a request to review risky wires, call `get_high_risk_wires` with the
   requested minimum risk (80 if unspecified). Its interactive panel is the
   review surface. Do not duplicate the panel as a Markdown table.
2. When asked to investigate a wire or when the panel sends a risk question,
   call `analyze_wire` with that wire's ID and the user's question. This invokes
   the Azure Foundry banking investigator with the actual banking record.
   Clearly separate observed signals from hypotheses.
3. Hold requests must originate from the analyst's selection in the panel.
   `create_hold_request` is app-only. Do not attempt to call it yourself or
   recreate it with scripts, HTTP requests, or another tool.
4. A successful hold request is only `PENDING_APPROVAL`. Never claim the wire
   is held, approved, released, or stopped. No approval workflow or payment
   execution exists in this synthetic demo.
5. If a tool fails or times out, report the failure. Do not invent a successful
   result or automatically retry a hold submission.

All customers, wires, and risk signals in this demo are synthetic.
