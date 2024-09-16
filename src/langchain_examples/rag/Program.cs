using LangChain.Databases.Sqlite;
using LangChain.Extensions;
using LangChain.Providers;
using LangChain.Providers.Azure;
using LangChain.Providers.OpenAI;
using LangChain.Providers.OpenAI.Predefined;
using LangChain.DocumentLoaders;
using LangChain.Splitters.Text;
using static LangChain.Chains.Chain;

var (endpoint, apiKey) = new Settings().LoadSettings();
var provider = new AzureOpenAiProvider(apiKey: apiKey, endpoint: endpoint);
var llm = new AzureOpenAiChatModel(provider, id: "gpt-35-turbo");

var embeddingModel = new AzureOpenAiEmbeddingModel(provider,  id: "text-embedding-3-small");

var vectorDatabase = new SqLiteVectorDatabase(dataSource: "vectors.db");

var vectorCollection = await vectorDatabase.AddDocumentsFromAsync<PdfPigPdfLoader>(
    embeddingModel, 
    dimensions: 1536,
    dataSource: DataSource.FromUrl("https://canonburyprimaryschool.co.uk/wp-content/uploads/2016/01/Joanne-K.-Rowling-Harry-Potter-Book-1-Harry-Potter-and-the-Philosophers-Stone-EnglishOnlineClub.com_.pdf"),
    collectionName: "harrypotter", // Can be omitted, use if you want to have multiple collections
    textSplitter: null);

string promptText =
    @"Use the following pieces of context to answer the question at the end. If the answer is not in context 
    then just say that you don't know, don't try to make up an answer. Keep the answer as short as possible.

    {context}

    Question: {question}
    Helpful Answer:";


var chain =
    Set("Who was drinking a unicorn blood?")     
    | RetrieveSimilarDocuments(vectorCollection, embeddingModel, amount: 5)                                                      
    | CombineDocuments(outputKey: "context")     
    | Template(promptText)                                              
    | LLM(llm.UseConsoleForDebug());                                                         
var chainAnswer = await chain.RunAsync("text");

Console.WriteLine("Chain Answer:"+ chainAnswer);    
Console.WriteLine($"LLM usage: {llm.Usage}");   
Console.WriteLine($"Embedding model usage: {embeddingModel.Usage}");  

