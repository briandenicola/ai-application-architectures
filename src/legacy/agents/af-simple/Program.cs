
using Azure.Identity;

namespace Azure.AI.Projects;

public class SimpleAgent
{
    static async Task Main()
    {
        var connectionString = Environment.GetEnvironmentVariable("PROJECT_CONNECTION_STRING");
        var modelDeploymentName = Environment.GetEnvironmentVariable("PROJECT_MODEL_NAME") ?? "gpt-4.1.2";

        var client = new AgentsClient(connectionString, new DefaultAzureCredential());

        var agentResponse = await client.CreateAgentAsync(
            model: modelDeploymentName,
            name: "Simple Agent",
            instructions: "You are a helpful agent.",
            tools: new List<ToolDefinition> { new CodeInterpreterToolDefinition() });
        Agent agent = agentResponse.Value;

        var agentListResponse = await client.GetAgentsAsync();

        var threadResponse = await client.CreateThreadAsync();
        var thread = threadResponse.Value;

        var messageResponse = await client.CreateMessageAsync(
                                                thread.Id,
                                                MessageRole.User,
                                                "I need to solve the equation `3x + 11 = 14`. Can you help me?");
        var message = messageResponse.Value;

        var messagesListResponse = await client.GetMessagesAsync(thread.Id);
        var runResponse = await client.CreateRunAsync(
            thread.Id,
            agent.Id,
            additionalInstructions: "");
        ThreadRun run = runResponse.Value;

        do
        {

            await Task.Delay(TimeSpan.FromMilliseconds(500));
            runResponse = await client.GetRunAsync(thread.Id, runResponse.Value.Id);
        
        }while (runResponse.Value.Status == RunStatus.Queued
            || runResponse.Value.Status == RunStatus.InProgress);

        var afterRunMessagesResponse = await client.GetMessagesAsync(thread.Id);
        var messages = afterRunMessagesResponse.Value.Data;

        foreach (var threadMessage in messages)
        {
            Console.Write($"{threadMessage.CreatedAt:yyyy-MM-dd HH:mm:ss} - {threadMessage.Role,10}: ");
            foreach (MessageContent contentItem in threadMessage.ContentItems)
            {
                if (contentItem is MessageTextContent textItem)
                {
                    Console.Write(textItem.Text);
                }
                else if (contentItem is MessageImageFileContent imageFileItem)
                {
                    Console.Write($"<image from ID: {imageFileItem.FileId}");
                }
                Console.WriteLine();
            }
        }

        await client.DeleteThreadAsync(threadId: thread.Id);
        await client.DeleteAgentAsync(agentId: agent.Id);
    }
}