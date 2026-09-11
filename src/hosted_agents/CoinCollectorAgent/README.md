# Coin Collection Advisor

A small multi-agent demo built on **Microsoft Agent Framework** (.NET 10, C# 13) and deployed as a
**Foundry Hosted Agent** in Microsoft Foundry. Give it your collecting criteria — theme, budget,
grade, country — and a triage hub routes the request through seven specialist agents that search
a coin catalog, price-check and risk-flag candidates, cross-check them against your existing
collection, rank a shortlist, write up a recommendation, and (if you approve one) add it to your
watchlist.

## What it demonstrates

| Foundry feature | Where |
| --- | --- |
| **Models** | `gpt-4o-mini` for triage/search/valuation/portfolio/refine/watchlist, `gpt-4o` for the curator's final write-up — see [`ModelDeployments`](src/CoinAdvisor.Agent/Agents/CoinAdvisorWorkflowFactory.cs) |
| **Hosted Agents** | The whole workflow is packaged as one Foundry Agent Service hosted agent — see [`Program.cs`](src/CoinAdvisor.Agent/Program.cs) |
| **Tools** | `SearchCatalog`, `GetPriceGuide`, `GetOwnedCoins`, `AddToWatchlist` — see [`CoinTools.cs`](src/CoinAdvisor.Agent/Tools/CoinTools.cs) |
| **Memory** | `CollectorProfileProvider` injects the collector's saved preferences via `AIContextProvider` — see [`Memory/`](src/CoinAdvisor.Agent/Memory/CollectorProfileProvider.cs) |
| **Multi-agent orchestration** | A Handoff workflow (triage hub + 7 specialists) with a conditional loop-back — see [`AgentInstructions.Triage`](src/CoinAdvisor.Agent/Agents/AgentInstructions.cs) |

## Architecture

```
                     ┌─────────────┐
        ┌───────────▶│ triage_agent│◀───────────┐
        │            └─────┬───────┘            │
        │   (routes to exactly one specialist,   │
        │    every specialist hands back here)   │
        │                                        │
  intake_agent → search_agent → valuation_agent → portfolio_agent
                       ▲               │
                       └── relax & retry if <2 candidates survive
                                        │
                          refine_agent → curator_agent → watchlist_agent
```

`triage_agent`'s instructions encode the routing logic, including the one conditional loop:
if `valuation_agent` filters out too many candidates (overpriced, suspiciously cheap, or
high authenticity risk), triage sends control back to `search_agent` with relaxed constraints
instead of moving on.

## Prerequisites

- [.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0)
- A [Microsoft Foundry](https://azure.microsoft.com/products/ai-foundry) project with two model
  deployments (a cheap one and a stronger one — defaults assume `gpt-4o-mini` and `gpt-4o`)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) (`az login`) for local runs
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
  with the AI agent extension for deployment: `azd ext install azure.ai.agents`

## Run it locally

```bash
export FOUNDRY_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export FAST_MODEL_DEPLOYMENT="gpt-4o-mini"     # optional, this is the default
export STRONG_MODEL_DEPLOYMENT="gpt-4o"        # optional, this is the default

az login
dotnet run --project src/CoinAdvisor.Agent
```

In a second terminal, chat with it using the demo client. `dotnet run` on the Agent project
serves on `http://localhost:5262` by default (see `Properties/launchSettings.json`); if you
run it via `azd ai agent run` instead, it serves on `http://localhost:8088` (the client's
default if you omit the argument):

```bash
dotnet run --project src/CoinAdvisor.Client -- http://localhost:5262
```

Try: *"I'm looking for a Mercury Dime under $20, at least VF20."* — demo-user already owns a
1943-P Mercury Dime and is building the set by mint mark, so watch how `portfolio_agent` flags
the 1945-S as a set-completion opportunity instead of just the cheapest match.

## Deploy to Microsoft Foundry

```bash
azd auth login
azd provision   # creates a Foundry project, model deployment, and container registry if needed
azd deploy       # packages the agent as a container and deploys it to Foundry Agent Service
```

Once deployed, the agent is reachable at its own Foundry endpoint and testable from the Foundry
portal, with its own Entra identity and managed session persistence.

## Demo data

Everything under [`src/CoinAdvisor.Agent/Data`](src/CoinAdvisor.Agent/Data) is a static JSON
stand-in for real services (a catalog API, a price guide, a CRM):

- `coin-catalog.json` — 10 sample listings, including one deliberately-suspicious 1913 Liberty
  Head Nickel (asking $21,000 against a $4.2M fair value and a "High" authenticity risk) to show
  `valuation_agent` catching an outlier.
- `price-guide.json` — fair market value + authenticity risk per coin.
- `collector-profiles.json` — the demo collector's saved preferences (read via memory).
- `collections.json` — the demo collector's existing collection (read via the `GetOwnedCoins` tool).
- `watchlist.json` — starts empty; `AddToWatchlist` appends to it at runtime.

## A note on API surface

This scaffold targets Microsoft Agent Framework `1.12.0` / `Microsoft.Agents.AI.Foundry`
`1.12.0-preview.260629.1`, which are prerelease packages — some public API is still moving.
Every call in this repo (`AsAIAgent`, `AgentWorkflowBuilder`, `AIContextProvider`,
`AgentHost`/`AddFoundryResponses`) was checked against the actual installed assemblies rather
than assumed from docs, and the whole solution builds clean (`dotnet build`). If you bump the
package versions, re-check signatures with IntelliSense before assuming this still compiles.
