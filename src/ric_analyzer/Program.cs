using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;

var modelId = "gpt-4-turbo";
var coin = new Uri("https://github.com/briandenicola/openai-learnings/blob/main/src/ric_analyzer/img/coin.png?raw=true");

var (endpoint, apiKey) = new Settings().LoadSettings();

#pragma warning disable SKEXP0001, SKEXP0003, SKEXP0010, SKEXP0011, SKEXP0050, SKEXP0052
var kernel = Kernel.CreateBuilder()
                      .AddAzureOpenAIChatCompletion(modelId, endpoint, apiKey)
                      .Build();

var chat = kernel.GetRequiredService<IChatCompletionService>();
var history = new ChatHistory();
history.AddSystemMessage("You are an expert numismatist with a particular focus on Ancient Roman Imperial Coins with a dry sense of humor. You have been asked to analyze the following coin.");

var collectionItems= new ChatMessageContentItemCollection
{
    new TextContent("What is the inscription on the coin and who is the Emperor depicted? Tell me anything else you can deduce from the coin."),
    new ImageContent(coin)
};
history.AddUserMessage(collectionItems);

var result = await chat.GetChatMessageContentsAsync(history);
Console.WriteLine("Coin description: " + result[^1].Content);                      