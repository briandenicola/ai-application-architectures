using Azure.AI.Projects;
using CoinAdvisor.Agent.Memory;
using CoinAdvisor.Agent.Tools;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Workflows;
using Microsoft.Extensions.AI;

namespace CoinAdvisor.Agent.Agents;

public sealed record ModelDeployments(string FastModel, string StrongModel);

/// <summary>
/// Builds the coin-advisor's multi-agent handoff workflow: a triage hub plus seven
/// specialists, each of which always hands control back to triage when it's done.
/// The triage agent's own instructions (see <see cref="AgentInstructions.Triage"/>) encode
/// the conditional loop-back from valuation to search when too few candidates survive.
/// </summary>
public static class CoinAdvisorWorkflowFactory
{
    public static Workflow Create(
        AIProjectClient projectClient,
        CoinTools tools,
        CollectorProfileProvider profileProvider,
        ModelDeployments models)
    {
        AIFunction searchTool = AIFunctionFactory.Create(tools.SearchCatalog);
        AIFunction valuationTool = AIFunctionFactory.Create(tools.GetPriceGuide);
        AIFunction portfolioTool = AIFunctionFactory.Create(tools.GetOwnedCoins);
        AIFunction watchlistTool = AIFunctionFactory.Create(tools.AddToWatchlist);

        {
            var triageAgent = projectClient.AsAIAgent(
                model: models.FastModel,
                name: "triage_agent",
                instructions: AgentInstructions.Triage);

            // The intake agent is the one that reads the collector's raw request, so it's the
            // agent we attach the profile memory provider to; downstream specialists see the
            // injected profile summary via the shared handoff conversation history.
            var intakeAgent = projectClient.AsAIAgent(new ChatClientAgentOptions
            {
                Name = "intake_agent",
                ChatOptions = new ChatOptions
                {
                    ModelId = models.FastModel,
                    Instructions = AgentInstructions.Intake,
                },
                AIContextProviders = [profileProvider],
            });

            var searchAgent = projectClient.AsAIAgent(
                model: models.FastModel,
                name: "search_agent",
                instructions: AgentInstructions.Search,
                tools: [searchTool]);

            var valuationAgent = projectClient.AsAIAgent(
                model: models.FastModel,
                name: "valuation_agent",
                instructions: AgentInstructions.Valuation,
                tools: [valuationTool]);

            var portfolioAgent = projectClient.AsAIAgent(
                model: models.FastModel,
                name: "portfolio_agent",
                instructions: AgentInstructions.PortfolioFit,
                tools: [portfolioTool]);

            var refineAgent = projectClient.AsAIAgent(
                model: models.FastModel,
                name: "refine_agent",
                instructions: AgentInstructions.Refine);

            var curatorAgent = projectClient.AsAIAgent(
                model: models.StrongModel,
                name: "curator_agent",
                instructions: AgentInstructions.Curator);

            var watchlistAgent = projectClient.AsAIAgent(
                model: models.FastModel,
                name: "watchlist_agent",
                instructions: AgentInstructions.Watchlist,
                tools: [watchlistTool]);

            return AgentWorkflowBuilder
                .CreateHandoffBuilderWith(triageAgent)
                .WithHandoffs(triageAgent, [intakeAgent, searchAgent, valuationAgent, portfolioAgent, refineAgent, curatorAgent, watchlistAgent])
                .WithHandoff(intakeAgent, triageAgent)
                .WithHandoff(searchAgent, triageAgent)
                .WithHandoff(valuationAgent, triageAgent)
                .WithHandoff(portfolioAgent, triageAgent)
                .WithHandoff(refineAgent, triageAgent)
                .WithHandoff(curatorAgent, triageAgent)
                .WithHandoff(watchlistAgent, triageAgent)
                .Build();
        }
    }
}
