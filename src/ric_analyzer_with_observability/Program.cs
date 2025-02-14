using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using OpenTelemetry;
using OpenTelemetry.Logs;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using Spectre.Console;
#pragma warning disable SKEXP0050

var aspireEndpoint = "http://localhost:4317";
var modelId = "gpt-4-turbo";
var systemMessage = "You are an expert numismatist with a particular focus on Ancient Roman Imperial Coins with a dry sense of humor. You have been asked to analyze the following coin.";
var prompt = "What is the inscription on the coin and make a guess on the Emperor depicted? Tell me anything else you can deduce from the coin. It's okay to be wrong. These guys are long dead.";

var coin = new Uri("https://github.com/briandenicola/openai-learnings/blob/main/src/ric_analyzer/img/coin-2.png?raw=true");

var (endpoint, apiKey) = new Settings().LoadSettings();

var resourceBuilder = ResourceBuilder
    .CreateDefault()
    .AddService("RomanImperialCoinAnalyzer");

AppContext.SetSwitch("Microsoft.SemanticKernel.Experimental.GenAI.EnableOTelDiagnosticsSensitive", true);

using var traceProvider = Sdk.CreateTracerProviderBuilder()
    .SetResourceBuilder(resourceBuilder)
    .AddSource("Microsoft.SemanticKernel*")
    .AddOtlpExporter(options => options.Endpoint = new Uri(aspireEndpoint))
    .Build();

using var meterProvider = Sdk.CreateMeterProviderBuilder()
    .SetResourceBuilder(resourceBuilder)
    .AddMeter("Microsoft.SemanticKernel*")
    .AddConsoleExporter()
    .AddOtlpExporter(options => options.Endpoint = new Uri(aspireEndpoint))
    .Build();

using var loggerFactory = LoggerFactory.Create(builder =>
{
    builder.AddOpenTelemetry(options =>
    {
        options.SetResourceBuilder(resourceBuilder);
        options.AddConsoleExporter();
        options.AddOtlpExporter(options => options.Endpoint = new Uri(aspireEndpoint));
        options.IncludeFormattedMessage = true;
        options.IncludeScopes = true;
    });
    builder.SetMinimumLevel(LogLevel.Information);
});

var builder = Kernel.CreateBuilder();
builder.Services.AddSingleton(loggerFactory);
builder.AddAzureOpenAIChatCompletion(modelId, endpoint, apiKey);
            
var kernel = builder.Build();

var chat = kernel.GetRequiredService<IChatCompletionService>();
var history = new ChatHistory();
history.AddSystemMessage(systemMessage);
history.AddUserMessage(prompt);

var  requestSettings = new OpenAIPromptExecutionSettings()
{
    MaxTokens = 4096,    
};

var collectionItems= new ChatMessageContentItemCollection
{
    new TextContent(prompt),
    new ImageContent(coin)
};
history.AddUserMessage(collectionItems);

AnsiConsole.Markup("[bold blue]Hello, I am a Roman Imperial Coin Analyzer chatbot. I can help you with analyzing Roman Imperial Coins. Let's start with the coin analysis.[/]");
AnsiConsole.MarkupInterpolated($"[bold blue]Prompt: {prompt}[/]");
AnsiConsole.MarkupInterpolated($"[bold blue]Analyzing the following coin image: {coin.AbsoluteUri}[/]\n");

var result = await AnsiConsole.Progress().StartAsync(async ctx => {
    var task = ctx.AddTask("[green]Analyzing Coin with GPT...[/]");

    while (!task.IsFinished) {
        task.Increment(1.0);
        await Task.Delay(1000);
    }

    var chatResult = await chat.GetChatMessageContentAsync(history, requestSettings, kernel);
    task.StopTask();
    return chatResult;
});

if( result.Content is not null) {     
    AnsiConsole.MarkupInterpolated($"[bold yellow]{result.Content}[/]\n\n");                  
} else {
    Console.WriteLine("No response from the chatbot.");
}