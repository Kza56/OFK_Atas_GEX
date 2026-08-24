using OFK.Gex.Core.Health;

namespace OFK.Gex.Core;

public enum LoadDiagnosticSeverity
{
    Warning,
    Error,
}

public sealed record LoadDiagnostic(
    string Code,
    string Message,
    LoadDiagnosticSeverity Severity,
    string? Field = null);

public sealed record SnapshotSource(
    string? Path = null,
    DateTimeOffset? LastWriteTimeUtc = null,
    long? LengthBytes = null);

public sealed record SnapshotLoadResult(
    MarketSnapshot? Snapshot,
    HealthState State,
    IReadOnlyList<LoadDiagnostic> Diagnostics,
    SnapshotSource Source)
{
    public bool IsSuccess => Snapshot is not null &&
        State is HealthState.Healthy or HealthState.Partial or HealthState.Stale;
}
