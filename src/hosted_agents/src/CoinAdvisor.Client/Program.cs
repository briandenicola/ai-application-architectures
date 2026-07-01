using System.Text.Json;
using System.Text.Json.Nodes;

var baseUrl = args.Length > 0 ? args[0] : Environment.GetEnvironmentVariable("COIN_ADVISOR_URL") ?? "http://localhost:8088";
var responsesUrl = $"{baseUrl.TrimEnd('/')}/responses";

Console.WriteLine($"Coin Collection Advisor demo client — talking to {responsesUrl}");
Console.WriteLine("Try: \"I'm looking for a Mercury Dime under $20 in at least VF20\"");
Console.WriteLine("Type 'exit' to quit.\n");

using var http = new HttpClient();
string? previousResponseId = null;

while (true)
{
    Console.Write("you> ");
    var input = Console.ReadLine();
    if (string.IsNullOrWhiteSpace(input) || input.Equals("exit", StringComparison.OrdinalIgnoreCase))
        break;

    var requestBody = new JsonObject
    {
        ["input"] = input,
        ["previous_response_id"] = previousResponseId,
    };

    using var response = await http.PostAsync(
        responsesUrl,
        new StringContent(requestBody.ToJsonString(), System.Text.Encoding.UTF8, "application/json"));

    var responseText = await response.Content.ReadAsStringAsync();

    if (!response.IsSuccessStatusCode)
    {
        Console.WriteLine($"[HTTP {(int)response.StatusCode}] {responseText}");
        continue;
    }

    var responseJson = JsonNode.Parse(responseText)!.AsObject();
    previousResponseId = responseJson["id"]?.GetValue<string>();

    var outputText = ExtractOutputText(responseJson);
    Console.WriteLine($"advisor> {outputText}\n");
}

static string ExtractOutputText(JsonObject response)
{
    if (response["output"] is not JsonArray outputItems)
        return "(no output returned — see raw response with COIN_ADVISOR_DEBUG=1)";

    var texts = new List<string>();
    foreach (var item in outputItems)
    {
        if (item?["content"] is not JsonArray contentItems)
            continue;

        foreach (var content in contentItems)
        {
            var text = content?["text"]?.GetValue<string>();
            if (!string.IsNullOrWhiteSpace(text))
                texts.Add(text);
        }
    }

    return texts.Count > 0 ? string.Join("\n", texts) : "(agent responded with no text output)";
}
