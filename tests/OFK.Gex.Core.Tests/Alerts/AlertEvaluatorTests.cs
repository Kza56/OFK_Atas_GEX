using OFK.Gex.Core.Alerts;
using OFK.Gex.Core.Health;

namespace OFK.Gex.Core.Tests.Alerts;

public sealed class AlertEvaluatorTests
{
    private static readonly DateTimeOffset RegularTime =
        new(2026, 5, 1, 16, 0, 0, TimeSpan.Zero);

    [Theory]
    [InlineData(99, 100, true)]
    [InlineData(101, 100, true)]
    [InlineData(99, 101, true)]
    [InlineData(101, 99, true)]
    [InlineData(100, 101, false)]
    [InlineData(100, 99, false)]
    [InlineData(99, 99.5, false)]
    [InlineData(101, 100.5, false)]
    public void Crossing_boundary_semantics_match_legacy(
        decimal previous,
        decimal current,
        bool expected)
    {
        Assert.Equal(expected, AlertEvaluator.Crossed(previous, current, 100m));
    }

    [Fact]
    public void Missing_or_nonpositive_level_never_crosses()
    {
        Assert.False(AlertEvaluator.Crossed(99m, 101m, null));
        Assert.False(AlertEvaluator.Crossed(99m, 101m, -1m));
        Assert.False(AlertEvaluator.Crossed(99m, 101m, 0m));
    }

    [Fact]
    public void Gamma_flip_crossing_emits_expected_family()
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            PreviousClose = 99m,
            CurrentClose = 100m,
            GammaFlip = 100m,
        });

        AssertDecision(result, "gamma_flip", AlertFamily.GammaFlipCrossing);
    }

    [Fact]
    public void Call_and_put_wall_crossings_are_both_evaluated()
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            PreviousClose = 90m,
            CurrentClose = 110m,
            CallWallIntraday = 105m,
            PutWallIntraday = 95m,
        });

        AssertDecision(result, "call_wall_id", AlertFamily.WallCrossing);
        AssertDecision(result, "put_wall_id", AlertFamily.WallCrossing);
    }

    [Fact]
    public void Ctrans_and_ptrans_crossings_are_both_evaluated()
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            PreviousClose = 90m,
            CurrentClose = 110m,
            CTransIntraday = 105m,
            PTransIntraday = 95m,
        });

        AssertDecision(result, "c_trans", AlertFamily.TransitionCrossing);
        AssertDecision(result, "p_trans", AlertFamily.TransitionCrossing);
    }

    [Fact]
    public void Volume_flow_crossing_uses_first_gex_extension()
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            PreviousClose = 99m,
            CurrentClose = 101m,
            GexExtension1 = 100m,
        });

        AssertDecision(result, "vol_flow", AlertFamily.VolumeFlow);
    }

    [Theory]
    [InlineData(101.25, true)]
    [InlineData(101.5, false)]
    public void Pin_proximity_is_inclusive_at_configured_tick_boundary(
        decimal pin,
        bool expected)
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            PreviousClose = 100m,
            CurrentClose = 100m,
            TickSize = 0.25m,
            PinStrike0Dte = pin,
        });

        Assert.Equal(expected, HasDecision(result, "pin_0dte"));
    }

    [Theory]
    [InlineData(18, false)]
    [InlineData(19, true)]
    [InlineData(20, true)]
    [InlineData(21, false)]
    public void Charm_proximity_only_emits_during_legacy_last_hour_period(
        int hourUtc,
        bool expected)
    {
        var result = AlertEvaluator.Evaluate(
            new AlertEvaluationInput
            {
                PreviousClose = 100m,
                CurrentClose = 100m,
                TickSize = 0.25m,
                CharmMagnet0Dte = 103.75m,
            },
            new DateTimeOffset(2026, 5, 1, hourUtc, 0, 0, TimeSpan.Zero));

        Assert.Equal(expected, HasDecision(result, "charm_magnet"));
    }

    [Theory]
    [InlineData(91, "ok", "ivr_high")]
    [InlineData(9, "partial", "ivr_low")]
    [InlineData(90, "ok", null)]
    [InlineData(10, "ok", null)]
    [InlineData(95, "insufficient", null)]
    public void Ivr_extreme_requires_strict_boundary_and_usable_status(
        decimal ivr,
        string status,
        string? expectedKey)
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            IvRankIntraday = ivr,
            IvRankIntradayStatus = status,
        });

        Assert.Equal(expectedKey is not null, HasDecision(result, expectedKey));
    }

    [Theory]
    [InlineData(0.01, false)]
    [InlineData(0.0101, true)]
    public void Backwardation_boundary_is_strict(decimal slope, bool expected)
    {
        var result = Evaluate(new AlertEvaluationInput { TermIntradaySlope = slope });

        Assert.Equal(expected, HasDecision(result, "term_back"));
        if (expected)
        {
            AssertDecision(result, "term_back", AlertFamily.TermBackwardation);
        }
    }

    [Theory]
    [InlineData(0.05, false)]
    [InlineData(0.0501, true)]
    public void Skew_boundary_is_strict(decimal skew, bool expected)
    {
        var result = Evaluate(new AlertEvaluationInput { Skew25dIntraday = skew });

        Assert.Equal(expected, HasDecision(result, "skew_high"));
        if (expected)
        {
            AssertDecision(result, "skew_high", AlertFamily.SkewExtreme);
        }
    }

    [Theory]
    [InlineData("normal", "extreme", true)]
    [InlineData("extreme", "extreme", false)]
    [InlineData(null, "extreme", true)]
    [InlineData("normal", "elevated", false)]
    public void Vix_alert_only_emits_on_transition_into_extreme(
        string? previous,
        string current,
        bool expected)
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            PreviousVixRegime = previous,
            VixRegime = current,
            Vix = 42m,
            VixDayOverDayChange = 8m,
        });

        Assert.Equal(expected, HasDecision(result, "vix_extreme"));
        Assert.Equal(current, result.NextVixRegime);
        if (expected)
        {
            AssertDecision(result, "vix_extreme", AlertFamily.VixRegime);
        }
    }

    [Fact]
    public void Macro_blackout_and_imminent_event_are_distinct_decisions()
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            MacroInBlackout = true,
            MacroNextEventTitle = "FOMC",
            MacroMinutesToNext = 30,
        });

        AssertDecision(result, "macro_blackout", AlertFamily.MacroBlackout);
        AssertDecision(result, "macro_imminent", AlertFamily.MacroBlackout);
    }

    [Theory]
    [InlineData(0, false)]
    [InlineData(1, true)]
    [InlineData(30, true)]
    [InlineData(31, false)]
    public void Imminent_macro_period_matches_legacy(int minutes, bool expected)
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            MacroNextEventTitle = "CPI",
            MacroMinutesToNext = minutes,
        });

        Assert.Equal(expected, HasDecision(result, "macro_imminent"));
    }

    [Theory]
    [MemberData(nameof(HealthDecisionCases))]
    public void Data_health_states_map_to_pure_alert_decisions(
        HealthState state,
        string? expectedKey)
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            Health = new HealthResult(
                state,
                $"health:{state}",
                RegularTime.AddMinutes(-15),
                TimeSpan.FromMinutes(15)),
            IntradayLoopRunning = true,
        });

        Assert.Equal(expectedKey is not null, HasDecision(result, expectedKey));
        if (expectedKey is not null)
        {
            AssertDecision(result, expectedKey, AlertFamily.DataHealth);
        }
    }

    public static TheoryData<HealthState, string?> HealthDecisionCases => new()
    {
        { HealthState.Missing, "data_missing" },
        { HealthState.Invalid, "data_invalid" },
        { HealthState.SchemaMismatch, "schema_mismatch" },
        { HealthState.Error, "data_error" },
        { HealthState.Partial, "data_partial" },
        { HealthState.Stale, "stale_data" },
        { HealthState.Healthy, null },
    };

    [Fact]
    public void Stale_alert_requires_intraday_loop_by_default()
    {
        var input = new AlertEvaluationInput
        {
            Health = new HealthResult(
                HealthState.Stale,
                "stale",
                RegularTime.AddMinutes(-15),
                TimeSpan.FromMinutes(15)),
            IntradayLoopRunning = false,
        };

        var defaultResult = Evaluate(input);
        var optInResult = AlertEvaluator.Evaluate(
            input,
            RegularTime,
            new AlertOptions { RequireIntradayLoopForStaleAlert = false });

        Assert.False(HasDecision(defaultResult, "stale_data"));
        Assert.True(HasDecision(optInResult, "stale_data"));
    }

    [Theory]
    [InlineData(102.5, 100, false, true, true)]
    [InlineData(102.5, 100, true, false, true)]
    [InlineData(105, 100, true, false, true)]
    [InlineData(105.25, 100, true, false, false)]
    public void Predictive_approach_hysteresis_matches_legacy(
        decimal price,
        decimal level,
        bool wasInZone,
        bool shouldAlert,
        bool expectedInZone)
    {
        var transition = AlertEvaluator.EvaluateApproach(
            price,
            level,
            tickSize: 0.25m,
            proximityTicks: 10,
            wasInZone);

        Assert.Equal(shouldAlert, transition.ShouldAlert);
        Assert.Equal(expectedInZone, transition.IsInZone);
    }

    [Fact]
    public void Evaluate_updates_predictive_state_without_external_mutation()
    {
        var initialStates = new Dictionary<string, bool>
        {
            ["gamma_flip_approach"] = false,
        };
        var result = AlertEvaluator.Evaluate(
            new AlertEvaluationInput
            {
                PreviousClose = 96m,
                CurrentClose = 97.5m,
                GammaFlip = 100m,
                TickSize = 0.25m,
                ApproachStates = initialStates,
            },
            RegularTime);

        AssertDecision(result, "gamma_flip_approach", AlertFamily.PredictiveProximity);
        Assert.True(result.NextApproachStates["gamma_flip_approach"]);
        Assert.False(initialStates["gamma_flip_approach"]);
    }

    [Fact]
    public void Missing_or_invalid_inputs_do_not_emit_false_market_alerts()
    {
        var result = Evaluate(new AlertEvaluationInput
        {
            PreviousClose = 99m,
            CurrentClose = 101m,
            TickSize = 0m,
            GammaFlip = null,
            CallWallIntraday = 0m,
            PutWallIntraday = -1m,
            CTransIntraday = null,
            PTransIntraday = 0m,
            PinStrike0Dte = null,
            CharmMagnet0Dte = -1m,
            IvRankIntraday = null,
            TermIntradaySlope = null,
            Skew25dIntraday = null,
            VixRegime = null,
            GexExtension1 = null,
        });

        Assert.Empty(result.Decisions);
    }

    [Fact]
    public void Disabling_an_alert_family_suppresses_it()
    {
        var result = AlertEvaluator.Evaluate(
            new AlertEvaluationInput
            {
                PreviousClose = 99m,
                CurrentClose = 101m,
                GammaFlip = 100m,
            },
            RegularTime,
            new AlertOptions
            {
                CrossGammaFlip = false,
                PredictiveAlerts = false,
            });

        Assert.DoesNotContain(
            result.Decisions,
            decision => decision.Family == AlertFamily.GammaFlipCrossing);
    }

    [Theory]
    [InlineData(101.25, 0.25, 5, true)]
    [InlineData(101.5, 0.25, 5, false)]
    [InlineData(100, 0, 5, false)]
    [InlineData(100, 0.25, 0, false)]
    public void Proximity_helper_has_explicit_boundaries(
        decimal level,
        decimal tick,
        int ticks,
        bool expected)
    {
        Assert.Equal(
            expected,
            AlertEvaluator.IsWithinProximity(100m, level, tick, ticks));
    }

    private static AlertEvaluationResult Evaluate(AlertEvaluationInput input) =>
        AlertEvaluator.Evaluate(
            input,
            RegularTime,
            new AlertOptions { PredictiveAlerts = false });

    private static bool HasDecision(AlertEvaluationResult result, string? key) =>
        key is not null && result.Decisions.Any(decision => decision.Key == key);

    private static void AssertDecision(
        AlertEvaluationResult result,
        string key,
        AlertFamily family)
    {
        var decision = Assert.Single(result.Decisions, candidate => candidate.Key == key);
        Assert.Equal(family, decision.Family);
        Assert.False(string.IsNullOrWhiteSpace(decision.Message));
    }
}
