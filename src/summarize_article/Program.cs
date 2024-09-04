using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.OpenAI;

var modelId = "gpt-4-turbo";
var systemMessage = "You are an expert in Ancient Roman History with a dry English sense of humor. You have been asked to summarize the following book.";
var prompt = "Summarize the following text in 100 words or less.";
var spinner = new ConsoleSpinner();

//var article = new Uri("https://raw.githubusercontent.com/briandenicola/openai-learnings/main/src/summarize_article/docs/livy-book-one-chapter-one.txt");
var article = new Uri("https://raw.githubusercontent.com/briandenicola/openai-learnings/main/src/summarize_article/docs/history-of-rome-podcast-episode-one.txt");

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

var content = await new HttpClient().GetStringAsync(article);
var collectionItems= new ChatMessageContentItemCollection
{
    new TextContent(prompt + content),
};
history.AddUserMessage(collectionItems);

Console.WriteLine("Hello, I am a Ancient Historian Chatbot. I can help you with your questions about Ancient Rome.");
Console.WriteLine($"Prompt: {prompt}");
Console.WriteLine($"Analyzing the following article:");
Console.WriteLine($"{content.Substring(0, 500)}");

Console.WriteLine("Please wait while analyzing book...\n");

spinner.Start();
var result = await chat.GetChatMessageContentAsync(history, requestSettings, kernel);
spinner.Stop();

Console.WriteLine($"Reply: {result.Content}");                
