namespace CoinAdvisor.Agent.Models;

public sealed record CoinListing(
    string CoinId,
    string Name,
    string Country,
    int Year,
    string Mint,
    string Metal,
    string Theme,
    string Grade,
    decimal AskingPrice,
    string ListedBy);

public sealed record PriceGuideEntry(
    string CoinId,
    string Grade,
    decimal FairMarketValue,
    string AuthenticityRisk);

public sealed record OwnedCoin(
    string CoinId,
    string Name,
    string Theme,
    string AcquiredGrade);

public sealed record CollectorProfile(
    string UserId,
    string DisplayName,
    List<string> FavoriteThemes,
    List<string> FavoriteCountries,
    List<string> PreferredMetals,
    decimal TypicalBudget,
    string MinAcceptableGrade,
    string Notes);

public sealed record WatchlistEntry(
    string UserId,
    string CoinId,
    string Name,
    decimal AskingPrice,
    DateTimeOffset AddedAt);
