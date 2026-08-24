namespace OFK.Gex.Core.Tests.Fixtures;

internal static class FixtureFiles
{
    internal static string NqGolden => Get("full_levels_NQ_golden.json");

    internal static string EsGolden => Get("full_levels_ES_golden.json");

    internal static string ReadNqGolden() => File.ReadAllText(NqGolden);

    internal static string ReadEsGolden() => File.ReadAllText(EsGolden);

    private static string Get(string fileName) =>
        Path.Combine(AppContext.BaseDirectory, "Fixtures", fileName);
}
