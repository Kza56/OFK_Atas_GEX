using OFK.Gex.Core.Health;

namespace OFK.Gex.Core.Tests.Health;

public sealed class HealthEvaluatorTests
{
    private static readonly DateTimeOffset Now =
        new(2026, 5, 1, 16, 0, 0, TimeSpan.Zero);

    [Theory]
    [MemberData(nameof(PrecedenceCases))]
    public void Health_precedence_is_deterministic(
        HealthEvaluationInput input,
        HealthState expected)
    {
        Assert.Equal(expected, HealthEvaluator.Evaluate(input, Now).State);
    }

    public static TheoryData<HealthEvaluationInput, HealthState> PrecedenceCases => new()
    {
        {
            HealthyInput() with
            {
                SourceExists = false,
                JsonIsValid = false,
                SchemaVersion = "9.0",
                DataQuality = "error",
            },
            HealthState.Missing
        },
        {
            HealthyInput() with
            {
                JsonIsValid = false,
                SchemaVersion = "9.0",
                DataQuality = "error",
            },
            HealthState.Invalid
        },
        {
            HealthyInput() with
            {
                SchemaVersion = "9.0",
                DataQuality = "error",
            },
            HealthState.SchemaMismatch
        },
        {
            HealthyInput() with
            {
                DataQuality = "error",
                LastUpdateUtc = Now.AddHours(-2),
            },
            HealthState.Error
        },
        {
            HealthyInput() with
            {
                DataQuality = "partial",
                LastUpdateUtc = Now.AddHours(-2),
            },
            HealthState.Partial
        },
        {
            HealthyInput() with { LastUpdateUtc = Now.AddMinutes(-11) },
            HealthState.Stale
        },
        { HealthyInput(), HealthState.Healthy },
    };

    [Fact]
    public void File_timestamp_is_used_when_json_timestamp_is_absent()
    {
        var result = HealthEvaluator.Evaluate(
            HealthyInput() with
            {
                LastUpdateUtc = null,
                FileLastWriteUtc = Now.AddMinutes(-4),
            },
            Now);

        Assert.Equal(HealthState.Healthy, result.State);
        Assert.Equal(Now.AddMinutes(-4), result.EffectiveTimestamp);
        Assert.Equal(TimeSpan.FromMinutes(4), result.Age);
    }

    [Fact]
    public void Missing_both_timestamps_is_partial_not_silently_healthy()
    {
        var result = HealthEvaluator.Evaluate(
            HealthyInput() with
            {
                LastUpdateUtc = null,
                FileLastWriteUtc = null,
            },
            Now);

        Assert.Equal(HealthState.Partial, result.State);
        Assert.Contains("timestamp", result.Reason, StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData(5, HealthState.Healthy)]
    [InlineData(6, HealthState.Invalid)]
    public void Future_timestamp_tolerance_is_explicit(
        int minutesInFuture,
        HealthState expected)
    {
        var result = HealthEvaluator.Evaluate(
            HealthyInput() with { LastUpdateUtc = Now.AddMinutes(minutesInFuture) },
            Now);

        Assert.Equal(expected, result.State);
    }

    [Fact]
    public void Partial_quality_does_not_hide_invalid_future_timestamp()
    {
        var result = HealthEvaluator.Evaluate(
            HealthyInput() with
            {
                DataQuality = "partial",
                LastUpdateUtc = Now.AddMinutes(6),
            },
            Now);

        Assert.Equal(HealthState.Invalid, result.State);
    }

    [Fact]
    public void Stale_threshold_is_strictly_greater_than_ten_minutes()
    {
        var atThreshold = HealthEvaluator.Evaluate(
            HealthyInput() with { LastUpdateUtc = Now.AddMinutes(-10) },
            Now);
        var pastThreshold = HealthEvaluator.Evaluate(
            HealthyInput() with
            {
                LastUpdateUtc = Now.AddMinutes(-10).AddTicks(-1),
            },
            Now);

        Assert.Equal(HealthState.Healthy, atThreshold.State);
        Assert.Equal(HealthState.Stale, pastThreshold.State);
    }

    private static HealthEvaluationInput HealthyInput() => new()
    {
        SourceExists = true,
        JsonIsValid = true,
        ExpectedSchemaVersion = "1.0",
        SchemaVersion = "1.0",
        DataQuality = "ok",
        LastUpdateUtc = Now.AddMinutes(-1),
        FileLastWriteUtc = Now.AddMinutes(-2),
        StaleAfter = TimeSpan.FromMinutes(10),
        FutureTolerance = TimeSpan.FromMinutes(5),
    };
}
