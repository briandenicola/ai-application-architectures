using CoinAdvisor.Agent.Data;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;

namespace CoinAdvisor.Agent.Memory;

/// <summary>
/// Injects the collector's saved profile (favorite themes, budget, grade floor) into the
/// conversation at the start of every turn, so the agents can fill in unstated criteria.
/// This is the "read" side of memory; writes happen through explicit tools instead, since
/// heuristically scraping preferences out of free text is unreliable for a demo.
/// </summary>
public sealed class CollectorProfileProvider(JsonDataStore store, string defaultUserId = "demo-user")
    : AIContextProvider(provideInputMessageFilter: null, storeInputRequestMessageFilter: null, storeInputResponseMessageFilter: null)
{
    private readonly ProviderSessionState<State> _sessionState = new(
        stateInitializer: _ => new State { UserId = defaultUserId },
        stateKey: nameof(CollectorProfileProvider));

    protected override ValueTask<AIContext> ProvideAIContextAsync(InvokingContext context, CancellationToken cancellationToken = default)
    {
        var state = _sessionState.GetOrInitializeState(context.Session);
        var profile = store.FindCollectorProfile(state.UserId);

        if (profile is null)
            return new ValueTask<AIContext>(new AIContext());

        var summary =
            $"""
            Collector profile for {profile.DisplayName} (userId: {profile.UserId}):
            - Favorite themes: {string.Join(", ", profile.FavoriteThemes)}
            - Favorite countries: {string.Join(", ", profile.FavoriteCountries)}
            - Preferred metals: {string.Join(", ", profile.PreferredMetals)}
            - Typical budget per coin: ${profile.TypicalBudget}
            - Minimum acceptable grade: {profile.MinAcceptableGrade}
            - Notes: {profile.Notes}

            Use this profile to fill in any criteria the collector didn't state explicitly.
            Explicit criteria from the collector's own message always take priority over the profile.
            """;

        return new ValueTask<AIContext>(new AIContext
        {
            Messages = [new ChatMessage(ChatRole.User, summary)]
        });
    }

    protected override ValueTask StoreAIContextAsync(InvokedContext context, CancellationToken cancellationToken = default) =>
        ValueTask.CompletedTask;

    private sealed class State
    {
        public string UserId { get; set; } = "demo-user";
    }
}
