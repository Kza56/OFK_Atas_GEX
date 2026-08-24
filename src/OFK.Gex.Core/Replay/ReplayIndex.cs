using System.Globalization;
using System.Text.RegularExpressions;

namespace OFK.Gex.Core.Replay;

public sealed record ReplaySnapshot(
    string Symbol,
    DateOnly SessionDate,
    TimeOnly Time,
    string Path)
{
    /// <summary>
    /// A timezone-neutral timestamp matching the date and HHmm encoded in the
    /// filename. Consumers decide which exchange timezone applies.
    /// </summary>
    public DateTime Timestamp => SessionDate.ToDateTime(Time, DateTimeKind.Unspecified);
}

/// <summary>
/// Portable parser/indexer for SYMBOL_full_levels_YYYYMMDD_HHMM.json files.
/// </summary>
public static partial class ReplayIndex
{
    [GeneratedRegex(
        "^(?<symbol>NQ|ES)_full_levels_(?<date>[0-9]{8})_(?<time>[0-9]{4})[.]json$",
        RegexOptions.CultureInvariant | RegexOptions.IgnoreCase)]
    private static partial Regex SnapshotFileNamePattern();

    public static bool TryParse(string path, out ReplaySnapshot? snapshot)
    {
        snapshot = null;
        if (string.IsNullOrWhiteSpace(path))
        {
            return false;
        }

        string fileName;
        try
        {
            fileName = System.IO.Path.GetFileName(path);
        }
        catch (ArgumentException)
        {
            return false;
        }

        var match = SnapshotFileNamePattern().Match(fileName);
        if (!match.Success ||
            !DateOnly.TryParseExact(
                match.Groups["date"].Value,
                "yyyyMMdd",
                CultureInfo.InvariantCulture,
                DateTimeStyles.None,
                out var sessionDate) ||
            !TimeOnly.TryParseExact(
                match.Groups["time"].Value,
                "HHmm",
                CultureInfo.InvariantCulture,
                DateTimeStyles.None,
                out var time))
        {
            return false;
        }

        var symbol = match.Groups["symbol"].Value.ToUpperInvariant();
        snapshot = new ReplaySnapshot(symbol, sessionDate, time, path);
        return true;
    }

    /// <summary>
    /// Filters and orders candidate paths. Duplicate timestamps are resolved
    /// deterministically by retaining the ordinally smallest path.
    /// </summary>
    public static IReadOnlyList<ReplaySnapshot> Build(
        IEnumerable<string> paths,
        string symbol,
        DateOnly sessionDate)
    {
        ArgumentNullException.ThrowIfNull(paths);

        var normalizedSymbol = NormalizeSymbol(symbol);
        var candidates = new List<ReplaySnapshot>();
        foreach (var path in paths)
        {
            if (TryParse(path, out var snapshot) &&
                snapshot is not null &&
                string.Equals(snapshot.Symbol, normalizedSymbol, StringComparison.Ordinal) &&
                snapshot.SessionDate == sessionDate)
            {
                candidates.Add(snapshot);
            }
        }

        return candidates
            .OrderBy(candidate => candidate.Time)
            .ThenBy(candidate => candidate.Path, StringComparer.Ordinal)
            .GroupBy(candidate => candidate.Time)
            .Select(group => group.First())
            .ToArray();
    }

    /// <summary>
    /// Enumerates one directory without throwing for missing/inaccessible
    /// locations. Parsing and filtering are delegated to <see cref="Build"/>.
    /// </summary>
    public static IReadOnlyList<ReplaySnapshot> FromDirectory(
        string? directory,
        string symbol,
        DateOnly sessionDate)
    {
        if (string.IsNullOrWhiteSpace(directory) || !Directory.Exists(directory))
        {
            return [];
        }

        try
        {
            // Enumerate all top-level files and let the case-insensitive parser
            // decide. A "*.json" glob is case-sensitive on some filesystems.
            return Build(Directory.EnumerateFiles(directory, "*", SearchOption.TopDirectoryOnly), symbol, sessionDate);
        }
        catch (Exception exception) when (
            exception is IOException or UnauthorizedAccessException or ArgumentException)
        {
            return [];
        }
    }

    private static string NormalizeSymbol(string symbol)
    {
        if (string.IsNullOrWhiteSpace(symbol))
        {
            throw new ArgumentException("A replay symbol is required.", nameof(symbol));
        }

        return symbol.Trim().ToUpperInvariant();
    }
}
