using Microsoft.SemanticKernel;

var modelId = "gpt-4";
var (endpoint, apiKey) = new Settings().LoadSettings();

Kernel kernel = Kernel.CreateBuilder()
                      .AddAzureOpenAIChatCompletion(modelId, endpoint, apiKey)
                      .Build();