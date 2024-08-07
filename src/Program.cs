using Microsoft.SemanticKernel;
using Microsoft.Extensions.Configuration;

var config  = new ConfigurationBuilder()
    .AddJsonFile("settings.json")
    .AddEnvironmentVariables()
    .Build();    

// task settings generates a Settings object from the settings.json file
// settings.json
// {
//   "OpenAI": {
//     "apiKey": "{{YOUR_API_KEY}}",
//     "modelId": "gpt-4o",
//     "endpoint": "https://westus3.api.cognitive.microsoft.com/"
//   }
// }



Settings? settings = config.GetRequiredSection("OpenAI").Get<Settings>();

if(settings is null)
{
    Console.WriteLine("Settings not found");
    return;
} 
else if( string.IsNullOrEmpty(settings.modelId) || string.IsNullOrEmpty(settings.endpoint) || string.IsNullOrEmpty(settings.apiKey))
{
    Console.WriteLine("Settings are not complete");
    return;
}

string modelId = settings.modelId;
string endpoint = settings.endpoint;
string apiKey = settings.apiKey;

Kernel kernel = Kernel.CreateBuilder()
                      .AddAzureOpenAIChatCompletion(modelId, endpoint, apiKey)
                      .Build();

Console.WriteLine("Hello, I am a Jokester chatbot. I can help you with jokes. Let's start with a knock-knock joke.");
string prompt = "Finish the following knock-knock joke. Knock, knock. Who's there? Dishes. Dishes who?";
Console.WriteLine($"Prompt: {prompt}");

var joke = await kernel.InvokePromptAsync(prompt);
Console.WriteLine($"Reply: {joke}");

public sealed class Settings
{
    public required  string modelId { get; set; }
    public required  string endpoint { get; set; }
    public required  string apiKey { get; set; }
}