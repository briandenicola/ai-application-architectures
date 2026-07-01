using System.ComponentModel;
using CoinAdvisor.Agent.Data;
using CoinAdvisor.Agent.Models;

namespace CoinAdvisor.Agent.Tools;

/// <summary>
/// Function tools shared across the coin-advisor agents. Grouped in one class because
/// they all read/write the same demo data store.
/// </summary>
public sealed class CoinTools(JsonDataStore store)
{
    // Coarse low-to-high grade ranking covering the grades used in the demo catalog.
    // Real numismatic grading has ~70 points (P1-MS70); this is intentionally simplified.
    private static readonly Dictionary<string, int> GradeRank = new(StringComparer.OrdinalIgnoreCase)
    {
        ["AG3"] = 5,
        ["G4"] = 10,
        ["Good"] = 10,
        ["VG8"] = 15,
        ["F12"] = 20,
        ["Fine"] = 20,
        ["VF20"] = 25,
        ["VF"] = 27,
        ["VF30"] = 28,
        ["XF40"] = 35,
        ["XF45"] = 36,
        ["AU50"] = 40,
        ["AU53"] = 42,
        ["AU55"] = 43,
        ["AU58"] = 45,
        ["MS60"] = 50,
        ["MS63"] = 53,
        ["MS65"] = 55,
    };

    [Description("Search the coin catalog for listings matching the given criteria. Any parameter can be left null to skip that filter.")]
    public IReadOnlyList<CoinListing> SearchCatalog(
        [Description("Collecting theme, e.g. 'Mercury Dime', 'Morgan Dollar', 'Ancient Roman'.")] string? theme = null,
        [Description("Country of origin, e.g. 'United States', 'Roman Empire'.")] string? country = null,
        [Description("Metal, e.g. 'Silver', 'Copper-Nickel'.")] string? metal = null,
        [Description("Minimum acceptable grade, e.g. 'VF20'. Listings below this grade are excluded.")] string? minGrade = null,
        [Description("Maximum asking price in USD. Listings above this price are excluded.")] decimal? maxPrice = null)
    {
        var results = store.LoadCatalog().AsEnumerable();

        if (!string.IsNullOrWhiteSpace(theme))
            results = results.Where(c => c.Theme.Contains(theme, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(country))
            results = results.Where(c => c.Country.Contains(country, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(metal))
            results = results.Where(c => c.Metal.Contains(metal, StringComparison.OrdinalIgnoreCase));

        if (!string.IsNullOrWhiteSpace(minGrade) && GradeRank.TryGetValue(minGrade, out var minRank))
            results = results.Where(c => !GradeRank.TryGetValue(c.Grade, out var rank) || rank >= minRank);

        if (maxPrice is not null)
            results = results.Where(c => c.AskingPrice <= maxPrice);

        return results.ToList();
    }

    [Description("Look up the fair-market-value price guide entry and authenticity risk rating for a specific coin by its catalog ID.")]
    public PriceGuideEntry? GetPriceGuide(
        [Description("The catalog coinId returned by SearchCatalog, e.g. 'MD-1916-D'.")] string coinId) =>
        store.LoadPriceGuide().FirstOrDefault(p => string.Equals(p.CoinId, coinId, StringComparison.OrdinalIgnoreCase));

    [Description("Get the coins the collector already owns, to avoid recommending duplicates and to spot set-completion opportunities.")]
    public IReadOnlyList<OwnedCoin> GetOwnedCoins(
        [Description("The collector's user ID.")] string userId) =>
        store.FindOwnedCoins(userId);

    [Description("Add a coin the collector approved to their watchlist for follow-up. Only call this after the collector has explicitly agreed to a specific coin.")]
    public WatchlistEntry AddToWatchlist(
        [Description("The collector's user ID.")] string userId,
        [Description("The catalog coinId to watch.")] string coinId,
        [Description("The coin's display name.")] string name,
        [Description("The asking price at the time it was added.")] decimal askingPrice) =>
        store.AddToWatchlist(userId, coinId, name, askingPrice);
}
