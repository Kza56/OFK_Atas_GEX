using OFK.Gex.Core.Health;
using OFK.Gex.Core.Tests.Fixtures;

namespace OFK.Gex.Core.Tests.Loading;

public sealed class SnapshotLoaderTests
{
    [Theory]
    [InlineData(null, "file.path")]
    [InlineData("", "file.path")]
    public void Blank_path_returns_missing_without_throwing(string? path, string code)
    {
        var result = SnapshotLoader.Load(path!, InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.Missing, result.State);
        Assert.False(result.IsSuccess);
        Assert.Null(result.Snapshot);
        Assert.Contains(result.Diagnostics, item => item.Code == code);
    }

    [Fact]
    public void Missing_file_returns_missing_without_throwing()
    {
        var path = Path.Combine(Path.GetTempPath(), $"ofk-missing-{Guid.NewGuid():N}.json");

        var result = SnapshotLoader.Load(path, InstrumentDefinitions.Nq);

        Assert.Equal(HealthState.Missing, result.State);
        Assert.Equal(path, result.Source.Path);
        Assert.Contains(result.Diagnostics, item => item.Code == "file.missing");
    }

    [Fact]
    public void File_loader_supplies_portable_source_metadata()
    {
        var directory = Directory.CreateTempSubdirectory("ofk-loader-");
        try
        {
            var path = Path.Combine(directory.FullName, "full_levels_NQ.json");
            File.WriteAllText(path, FixtureFiles.ReadNqGolden());
            var lastWrite = new DateTime(2026, 5, 1, 15, 58, 0, DateTimeKind.Utc);
            File.SetLastWriteTimeUtc(path, lastWrite);

            var result = SnapshotLoader.Load(path, InstrumentDefinitions.Nq);

            Assert.Equal(HealthState.Healthy, result.State);
            Assert.True(result.IsSuccess);
            Assert.NotNull(result.Snapshot);
            Assert.Equal(Path.GetFullPath(path), result.Source.Path);
            Assert.Equal(new DateTimeOffset(lastWrite), result.Source.LastWriteTimeUtc);
            Assert.Equal(new FileInfo(path).Length, result.Source.LengthBytes);
        }
        finally
        {
            directory.Delete(recursive: true);
        }
    }

    [Fact]
    public async Task Async_file_loader_matches_sync_contract()
    {
        var directory = Directory.CreateTempSubdirectory("ofk-loader-async-");
        try
        {
            var path = Path.Combine(directory.FullName, "full_levels_ES.json");
            await File.WriteAllTextAsync(path, FixtureFiles.ReadEsGolden());

            var result = await SnapshotLoader.LoadAsync(path, InstrumentDefinitions.Es);

            Assert.Equal(HealthState.Healthy, result.State);
            Assert.Equal(5590m, Assert.IsType<MarketSnapshot>(result.Snapshot).Gex.Spot);
            Assert.Equal(Path.GetFullPath(path), result.Source.Path);
            Assert.True(result.Source.LengthBytes > 0);
        }
        finally
        {
            directory.Delete(recursive: true);
        }
    }

    [Fact]
    public async Task Async_file_loader_honors_cancellation()
    {
        var directory = Directory.CreateTempSubdirectory("ofk-loader-cancel-");
        try
        {
            var path = Path.Combine(directory.FullName, "full_levels_NQ.json");
            await File.WriteAllTextAsync(path, FixtureFiles.ReadNqGolden());
            using var cancellation = new CancellationTokenSource();
            await cancellation.CancelAsync();

            await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
                SnapshotLoader.LoadAsync(
                    path,
                    InstrumentDefinitions.Nq,
                    cancellation.Token));
        }
        finally
        {
            directory.Delete(recursive: true);
        }
    }
}
