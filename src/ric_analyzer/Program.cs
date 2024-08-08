using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.OpenAI;

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
Console.WriteLine($"Reply: {result.Content}");                