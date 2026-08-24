using OFK.Gex.Core.Health;

namespace OFK.Gex.Core;

/// <summary>Portable file IO adapter around <see cref="SnapshotParser"/>.</summary>
public static class SnapshotLoader
{
    public static SnapshotLoadResult Load(string path, InstrumentSymbol symbol) =>
        Load(path, InstrumentDefinitions.Get(symbol));

    public static SnapshotLoadResult Load(string path, string symbol) =>
        Load(path, InstrumentDefinitions.Get(symbol));

    public static SnapshotLoadResult Load(string path, InstrumentDefinition instrument)
    {
        ArgumentNullException.ThrowIfNull(instrument);
        if (string.IsNullOrWhiteSpace(path))
        {
            return Missing(path, "file.path", "A snapshot path is required.");
        }

        if (!File.Exists(path))
        {
            return Missing(path, "file.missing", $"Snapshot file '{path}' does not exist.");
        }

        try
        {
            var info = new FileInfo(path);
            var source = new SnapshotSource(
                info.FullName,
                new DateTimeOffset(info.LastWriteTimeUtc, TimeSpan.Zero),
                info.Length);
            using var stream = new FileStream(
                info.FullName,
                FileMode.Open,
                FileAccess.Read,
                FileShare.ReadWrite | FileShare.Delete);
            return SnapshotParser.Parse(stream, instrument, source);
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return IoFailure(path, exception);
        }
    }

    public static async Task<SnapshotLoadResult> LoadAsync(
        string path,
        InstrumentDefinition instrument,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(instrument);
        if (string.IsNullOrWhiteSpace(path))
        {
            return Missing(path, "file.path", "A snapshot path is required.");
        }

        if (!File.Exists(path))
        {
            return Missing(path, "file.missing", $"Snapshot file '{path}' does not exist.");
        }

        try
        {
            var info = new FileInfo(path);
            var source = new SnapshotSource(
                info.FullName,
                new DateTimeOffset(info.LastWriteTimeUtc, TimeSpan.Zero),
                info.Length);
            var json = await File.ReadAllTextAsync(info.FullName, cancellationToken).ConfigureAwait(false);
            return SnapshotParser.Parse(json, instrument, source.Path) with { Source = source };
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception exception) when (exception is IOException or UnauthorizedAccessException)
        {
            return IoFailure(path, exception);
        }
    }

    private static SnapshotLoadResult Missing(string? path, string code, string message) =>
        new(
            null,
            HealthState.Missing,
            [new LoadDiagnostic(code, message, LoadDiagnosticSeverity.Error, "path")],
            new SnapshotSource(path));

    private static SnapshotLoadResult IoFailure(string path, Exception exception) =>
        new(
            null,
            HealthState.Invalid,
            [new LoadDiagnostic("file.io", exception.Message, LoadDiagnosticSeverity.Error, "path")],
            new SnapshotSource(path));
}
