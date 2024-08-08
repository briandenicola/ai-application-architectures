using Microsoft.SemanticKernel;

var modelId = "gpt-4o";
var (endpoint, apiKey) = new Settings().LoadSettings();

Kernel kernel = Kernel.CreateBuilder()
                      .AddAzureOpenAIChatCompletion(modelId, endpoint, apiKey)
                      .Build();

Console.WriteLine("Hello, I am a Jokester chatbot. I can help you with jokes. Let's start with a knock-knock joke.");
string prompt = "Finish the following knock-knock joke. Knock, knock. Who's there? Dishes. Dishes who?";
Console.WriteLine($"Prompt: {prompt}");

var completion = await kernel.InvokePromptAsync(prompt);
Console.WriteLine($"Reply: {completion}");



// task settings generates a Settings object from the settings.json file
// settings.json
// {
//   "OpenAI": {
//     "apiKey": "{{YOUR_API_KEY}}",
//     "endpoint": "https://westus3.api.cognitive.microsoft.com/"
//   }
// }