using Microsoft.Extensions.Configuration;

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