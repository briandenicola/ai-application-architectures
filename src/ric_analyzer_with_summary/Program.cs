using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.OpenAI;

#pragma warning disable SKEXP0050

var modelId = "gpt-4-turbo";
var systemMessage = "You are an expert numismatist with a particular focus on Ancient Roman Imperial Coins with a dry sense of humor. You have been asked to analyze the following coin.";
var prompt = "What is the inscription on the coin and who is the Emperor depicted? Tell me anything else you can deduce from the coin.";

var coin = new Uri("https://github.com/briandenicola/openai-learnings/blob/main/src/ric_analyzer/img/coin.png?raw=true");

var (endpoint, apiKey) = new Settings().LoadSettings();

var kernel = Kernel.CreateBuilder()
                      .AddAzureOpenAIChatCompletion(modelId, endpoint, apiKey)
                      .Build();

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
    
    Console.WriteLine("======== SamplePlugins - Conversation Summary Plugin - Summarize ========");
    
    KernelPlugin conversationSummaryPlugin = kernel.ImportPluginFromType<Microsoft.SemanticKernel.Plugins.Core.ConversationSummaryPlugin>();

    FunctionResult summary = await kernel.InvokeAsync(
        conversationSummaryPlugin["SummarizeConversation"], new() { ["input"] = result.Content });

    Console.WriteLine("Generated Summary:");
    Console.WriteLine(summary.GetValue<string>());
} else {
    Console.WriteLine("No response from the chatbot.");
}
