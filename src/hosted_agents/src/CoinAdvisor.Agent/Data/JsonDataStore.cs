using System.Text.Json;
using System.Threading;
using CoinAdvisor.Agent.Models;

namespace CoinAdvisor.Agent.Data;

/// <summary>
/// Minimal file-backed store standing in for a real catalog/price/CRM service in this demo.
/// Reads are cached in memory; writes (watchlist only) go straight back to disk.
/// </summary>
public sealed class JsonDataStore
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    private readonly string _dataDirectory;
    private readonly Lock _writeLock = new();

    public JsonDataStore(string dataDirectory) => _dataDirectory = dataDirectory;

    public IReadOnlyList<CoinListing> LoadCatalog() =>
        Load<CoinListing>("coin-catalog.json");

    public IReadOnlyList<PriceGuideEntry> LoadPriceGuide() =>
        Load<PriceGuideEntry>("price-guide.json");

    public CollectorProfile? FindCollectorProfile(string userId) =>
        Load<CollectorProfile>("collector-profiles.json").FirstOrDefault(p =>
            string.Equals(p.UserId, userId, StringComparison.OrdinalIgnoreCase));

    public IReadOnlyList<OwnedCoin> FindOwnedCoins(string userId)
    {
        var path = Path.Combine(_dataDirectory, "collections.json");
        using var stream = File.OpenRead(path);
        var collections = JsonSerializer.Deserialize<List<UserCollection>>(stream, JsonOptions) ?? [];
        return collections
            .FirstOrDefault(c => string.Equals(c.UserId, userId, StringComparison.OrdinalIgnoreCase))
            ?.OwnedCoins ?? [];
    }

    public WatchlistEntry AddToWatchlist(string userId, string coinId, string name, decimal askingPrice)
    {
        var entry = new WatchlistEntry(userId, coinId, name, askingPrice, DateTimeOffset.UtcNow);

        lock (_writeLock)
        {
            var path = Path.Combine(_dataDirectory, "watchlist.json");
            var existing = File.Exists(path)
                ? JsonSerializer.Deserialize<List<WatchlistEntry>>(File.ReadAllText(path), JsonOptions) ?? []
                : [];

            existing.Add(entry);
            File.WriteAllText(path, JsonSerializer.Serialize(existing, JsonOptions));
        }

        return entry;
    }

    private List<T> Load<T>(string fileName)
    {
        var path = Path.Combine(_dataDirectory, fileName);
        using var stream = File.OpenRead(path);
        return JsonSerializer.Deserialize<List<T>>(stream, JsonOptions) ?? [];
    }

    private sealed record UserCollection(string UserId, List<OwnedCoin> OwnedCoins);
}
