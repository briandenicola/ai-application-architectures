using Microsoft.SemanticKernel;
using Microsoft.Extensions.Configuration;

// task settings generates a Settings object from the settings.json file
// settings.json
// {
//   "OpenAI": {
//     "apiKey": "{{YOUR_API_KEY}}",
//     "modelId": "gpt-4o",
//     "endpoint": "https://westus3.api.cognitive.microsoft.com/"
//   }
// }

var (modelId, endpoint, apiKey) = new Settings().LoadSettings();

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
    public (string, string, string) LoadSettings()
    {
        var config  = new ConfigurationBuilder()
            .AddJsonFile("settings.json")
            .AddEnvironmentVariables()
            .Build(); 

        OpenAI? openai = config.GetRequiredSection("OpenAI").Get<OpenAI>();

        if( openai is null || string.IsNullOrEmpty(openai.modelId) || string.IsNullOrEmpty(openai.endpoint) || string.IsNullOrEmpty(openai.apiKey)) {
            throw new Exception("Settings not found or invalid");
        }

        return (openai.modelId, openai.endpoint, openai.apiKey);
    }
}
public sealed class OpenAI
{
    public required string modelId { get; set; }
    public required string endpoint { get; set; }
    public required string apiKey { get; set; }
}