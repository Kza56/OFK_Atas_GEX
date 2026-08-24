using OFK.Gex.Core.Replay;

namespace OFK.Gex.Core.Tests.Replay;

public sealed class ReplayIndexTests
{
    private static readonly DateOnly SessionDate = new(2026, 5, 1);

    [Theory]
    [InlineData("NQ_full_levels_20260501_0930.json", "NQ", 9, 30)]
    [InlineData("es_full_levels_20260501_1600.JSON", "ES", 16, 0)]
    public void Valid_snapshot_filename_is_parsed(
        string fileName,
        string expectedSymbol,
        int expectedHour,
        int expectedMinute)
    {
        var path = Path.Combine("snapshots", fileName);

        var parsed = ReplayIndex.TryParse(path, out var snapshot);

        Assert.True(parsed);
        var value = Assert.IsType<ReplaySnapshot>(snapshot);
        Assert.Equal(expectedSymbol, value.Symbol);
        Assert.Equal(SessionDate, value.SessionDate);
        Assert.Equal(new TimeOnly(expectedHour, expectedMinute), value.Time);
        Assert.Equal(DateTimeKind.Unspecified, value.Timestamp.Kind);
        Assert.Equal(path, value.Path);
    }

    [Theory]
    [InlineData("")]
    [InlineData("NQ_full_levels_20260501.json")]
    [InlineData("NQ_full_levels_20260501_930.json")]
    [InlineData("NQ_full_levels_20261301_0930.json")]
    [InlineData("NQ_full_levels_20260230_0930.json")]
    [InlineData("NQ_full_levels_20260501_2460.json")]
    [InlineData("NQ_full_levels_20260501_0930.json.tmp")]
    [InlineData("NQ-other-20260501-0930.json")]
    [InlineData("YM_full_levels_20260501_0930.json")]
    public void Malformed_snapshot_filename_is_rejected(string path)
    {
        Assert.False(ReplayIndex.TryParse(path, out var snapshot));
        Assert.Null(snapshot);
    }

    [Fact]
    public void Build_filters_symbol_and_date_then_orders_by_time()
    {
        var paths = new[]
        {
            Path.Combine("z", "NQ_full_levels_20260501_1545.json"),
            Path.Combine("z", "ES_full_levels_20260501_0930.json"),
            Path.Combine("z", "NQ_full_levels_20260430_0930.json"),
            Path.Combine("z", "NQ_full_levels_20260501_0815.json"),
            Path.Combine("z", "not-a-snapshot.json"),
            Path.Combine("z", "nq_full_levels_20260501_1200.json"),
        };

        var snapshots = ReplayIndex.Build(paths, "nq", SessionDate);

        Assert.Equal(
            [new TimeOnly(8, 15), new TimeOnly(12, 0), new TimeOnly(15, 45)],
            snapshots.Select(snapshot => snapshot.Time));
        Assert.All(snapshots, snapshot => Assert.Equal("NQ", snapshot.Symbol));
    }

    [Fact]
    public void Duplicate_times_keep_ordinally_smallest_path()
    {
        var smaller = Path.Combine("a", "NQ_full_levels_20260501_0930.json");
        var larger = Path.Combine("b", "NQ_full_levels_20260501_0930.json");

        var snapshots = ReplayIndex.Build([larger, smaller], "NQ", SessionDate);

        Assert.Equal(smaller, Assert.Single(snapshots).Path);
    }

    [Fact]
    public void Build_rejects_blank_symbol()
    {
        Assert.Throws<ArgumentException>(() =>
            ReplayIndex.Build([], " ", SessionDate));
    }

    [Fact]
    public void Missing_directory_returns_empty_result()
    {
        var path = Path.Combine(Path.GetTempPath(), $"ofk-absent-{Guid.NewGuid():N}");

        Assert.Empty(ReplayIndex.FromDirectory(path, "NQ", SessionDate));
        Assert.Empty(ReplayIndex.FromDirectory(null, "NQ", SessionDate));
    }

    [Fact]
    public void Directory_index_is_top_level_symbol_filtered_and_deterministic()
    {
        var directory = Directory.CreateTempSubdirectory("ofk-replay-");
        try
        {
            File.WriteAllText(
                Path.Combine(directory.FullName, "NQ_full_levels_20260501_1015.json"),
                "{}");
            File.WriteAllText(
                Path.Combine(directory.FullName, "NQ_full_levels_20260501_0845.json"),
                "{}");
            File.WriteAllText(
                Path.Combine(directory.FullName, "ES_full_levels_20260501_0900.json"),
                "{}");
            File.WriteAllText(
                Path.Combine(directory.FullName, "NQ_full_levels_20260502_0900.json"),
                "{}");
            File.WriteAllText(
                Path.Combine(directory.FullName, "notes.json"),
                "{}");
            var nested = Directory.CreateDirectory(Path.Combine(directory.FullName, "nested"));
            File.WriteAllText(
                Path.Combine(nested.FullName, "NQ_full_levels_20260501_0700.json"),
                "{}");

            var snapshots = ReplayIndex.FromDirectory(
                directory.FullName,
                "NQ",
                SessionDate);

            Assert.Equal(
                [new TimeOnly(8, 45), new TimeOnly(10, 15)],
                snapshots.Select(snapshot => snapshot.Time));
        }
        finally
        {
            directory.Delete(recursive: true);
        }
    }
}
