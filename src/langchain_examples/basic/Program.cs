using LangChain.Providers.Azure;

var (endpoint, apiKey) = new Settings().LoadSettings();

var provider = new AzureOpenAiProvider(apiKey: apiKey, endpoint: endpoint);
var llm = new AzureOpenAiChatModel(provider, id: "gpt-4o");

var result = await llm.GenerateAsync("What is a good name for a company that sells colourful socks?");

Console.WriteLine(result);