namespace OFK.Gex.Core.Health;

/// <summary>
/// Health states in strict precedence order. Lower-valued states take
/// precedence when more than one problem is present.
/// </summary>
public enum HealthState
{
    Missing = 0,
    Invalid = 1,
    SchemaMismatch = 2,
    Error = 3,
    Partial = 4,
    Stale = 5,
    Healthy = 6,
}

public sealed record HealthEvaluationInput
{
    public bool SourceExists { get; init; } = true;

    public bool JsonIsValid { get; init; } = true;

    public string ExpectedSchemaVersion { get; init; } = "1.0";

    public string? SchemaVersion { get; init; }

    public string? DataQuality { get; init; }

    public DateTimeOffset? LastUpdateUtc { get; init; }

    public DateTimeOffset? FileLastWriteUtc { get; init; }

    public TimeSpan StaleAfter { get; init; } = TimeSpan.FromMinutes(10);

    public TimeSpan FutureTolerance { get; init; } = TimeSpan.FromMinutes(5);
}

public sealed record HealthResult(
    HealthState State,
    string Reason,
    DateTimeOffset? EffectiveTimestamp = null,
    TimeSpan? Age = null)
{
    public bool IsUsable => State is HealthState.Healthy or HealthState.Partial or HealthState.Stale;
}

/// <summary>
/// Pure health/freshness policy. Precedence is Missing, Invalid,
/// SchemaMismatch, Error, Partial, Stale, Healthy.
/// </summary>
public static class HealthEvaluator
{
    public static HealthResult Evaluate(HealthEvaluationInput input, DateTimeOffset now)
    {
        ArgumentNullException.ThrowIfNull(input);

        if (!input.SourceExists)
        {
            return new HealthResult(HealthState.Missing, "Source file is missing.");
        }

        if (!input.JsonIsValid)
        {
            return new HealthResult(HealthState.Invalid, "Source JSON is invalid.");
        }

        var timestamp = input.LastUpdateUtc ?? input.FileLastWriteUtc;
        if (timestamp is not null && timestamp.Value - now > input.FutureTolerance)
        {
            return new HealthResult(
                HealthState.Invalid,
                "Source timestamp is unreasonably far in the future.",
                timestamp,
                now - timestamp.Value);
        }

        if (string.IsNullOrWhiteSpace(input.SchemaVersion) ||
            !string.Equals(
                input.SchemaVersion,
                input.ExpectedSchemaVersion,
                StringComparison.Ordinal))
        {
            return new HealthResult(
                HealthState.SchemaMismatch,
                $"Schema '{input.SchemaVersion ?? "<missing>"}' does not match expected '{input.ExpectedSchemaVersion}'.");
        }

        if (EqualsIgnoreCase(input.DataQuality, "error"))
        {
            return new HealthResult(HealthState.Error, "Pipeline data quality is error.");
        }

        if (EqualsIgnoreCase(input.DataQuality, "partial"))
        {
            return new HealthResult(
                HealthState.Partial,
                "Pipeline data quality is partial.",
                timestamp,
                timestamp is null ? null : NonNegativeAge(now, timestamp.Value));
        }

        if (timestamp is null)
        {
            return new HealthResult(
                HealthState.Partial,
                "No valid update timestamp or file timestamp is available.");
        }

        var age = NonNegativeAge(now, timestamp.Value);
        if (age > input.StaleAfter)
        {
            return new HealthResult(
                HealthState.Stale,
                $"Source is stale by {age.TotalMinutes:F0} minutes.",
                timestamp,
                age);
        }

        return new HealthResult(HealthState.Healthy, "Source is healthy.", timestamp, age);
    }

    private static TimeSpan NonNegativeAge(DateTimeOffset now, DateTimeOffset timestamp) =>
        now > timestamp ? now - timestamp : TimeSpan.Zero;

    private static bool EqualsIgnoreCase(string? value, string expected) =>
        string.Equals(value, expected, StringComparison.OrdinalIgnoreCase);
}
