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

#pragma warning disable SKEXP0050

var aspireEndpoint = "http://localhost:4317";
var modelId = "gpt-4-turbo";
var systemMessage = "You are an expert numismatist with a particular focus on Ancient Roman Imperial Coins with a dry sense of humor. You have been asked to analyze the following coin.";
var prompt = "What is the inscription on the coin and who is the Emperor depicted? Tell me anything else you can deduce from the coin.";

var coin = new Uri("https://github.com/briandenicola/openai-learnings/blob/main/src/ric_analyzer/img/coin.png?raw=true");

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
    .AddOtlpExporter(options => options.Endpoint = new Uri(aspireEndpoint))
    .Build();

using var loggerFactory = LoggerFactory.Create(builder =>
{
    builder.AddOpenTelemetry(options =>
    {
        options.SetResourceBuilder(resourceBuilder);
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

Console.WriteLine("Hello, I am a Roman Imperial Coin Analyzer chatbot. I can help you with analyzing Roman Imperial Coins. Let's start with the coin analysis.");
Console.WriteLine($"Prompt: {prompt}");
Console.WriteLine($"Analyzing the following coin image: {coin.AbsoluteUri}");
var result = await chat.GetChatMessageContentAsync(history, requestSettings, kernel);

if( result.Content is not null) { 
    history.AddUserMessage(result.Content);
    Console.WriteLine($"Reply: {result.Content}");                
    
    Console.WriteLine("======== Summarize: Conversation Summary Plugin ========");
    
    KernelPlugin conversationSummaryPlugin = kernel.ImportPluginFromType<Microsoft.SemanticKernel.Plugins.Core.ConversationSummaryPlugin>();

    FunctionResult summary = await kernel.InvokeAsync(
        conversationSummaryPlugin["SummarizeConversation"], new() { ["input"] = result.Content });

    Console.WriteLine(summary.GetValue<string>());
} else {
    Console.WriteLine("No response from the chatbot.");
}
