using Microsoft.Extensions.Configuration;

public sealed class Settings 
{
    public (string, string) LoadSettings()
    {
        var config  = new ConfigurationBuilder()
            .AddJsonFile("settings.json")
            .AddEnvironmentVariables()
            .Build(); 

        OpenAISettings? openai = config.GetRequiredSection("OpenAI").Get<OpenAISettings>();

        if( openai is null || string.IsNullOrEmpty(openai.embeddingEndpoint) || string.IsNullOrEmpty(openai.embeddingKey)) {
            throw new Exception("Settings not found or invalid");
        }

        return (openai.embeddingEndpoint, openai.embeddingKey);
    }
}
public sealed class OpenAISettings
{
    public required string embeddingEndpoint { get; set; }
    public required string embeddingKey { get; set; }
}