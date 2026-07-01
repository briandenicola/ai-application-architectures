using Azure.AI.AgentServer.Core;
using Azure.AI.Projects;
using Azure.Identity;
using CoinAdvisor.Agent.Agents;
using CoinAdvisor.Agent.Data;
using CoinAdvisor.Agent.Memory;
using CoinAdvisor.Agent.Tools;
using Microsoft.Agents.AI.Foundry.Hosting;
using Microsoft.Agents.AI.Workflows;

var projectEndpoint = new Uri(
    Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT")
    ?? throw new InvalidOperationException(
        "FOUNDRY_PROJECT_ENDPOINT is not set. Point it at your Microsoft Foundry project, " +
        "e.g. https://<account>.services.ai.azure.com/api/projects/<project>."));

var models = new ModelDeployments(
    FastModel: Environment.GetEnvironmentVariable("FAST_MODEL_DEPLOYMENT") ?? "gpt-4o-mini",
    StrongModel: Environment.GetEnvironmentVariable("STRONG_MODEL_DEPLOYMENT") ?? "gpt-4o");

var dataDirectory = Path.Combine(AppContext.BaseDirectory, "Data");
var store = new JsonDataStore(dataDirectory);
var tools = new CoinTools(store);
var profileProvider = new CollectorProfileProvider(store);

var projectClient = new AIProjectClient(projectEndpoint, new DefaultAzureCredential());
var workflow = CoinAdvisorWorkflowFactory.Create(projectClient, tools, profileProvider, models);

// AsAIAgent() adapts the workflow's graph execution to the standard AIAgent surface, so it
// can be hosted, run, and streamed exactly like a single agent would be.
var advisorAgent = workflow.AsAIAgent(name: "coin-collection-advisor");

var hostBuilder = AgentHost.CreateBuilder(args);
hostBuilder.Services.AddFoundryResponses(advisorAgent);
hostBuilder.RegisterProtocol("responses", endpoints => endpoints.MapFoundryResponses());

var host = hostBuilder.Build();
host.Run();
