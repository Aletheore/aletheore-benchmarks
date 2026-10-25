using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

// usage: CsScan <repo> <spec.json> <out.json>
// spec: { "projects": [ {"id":"p", "files":[rel...], "refs":["q",...], "usings":["Ns",...], "staticUsings":[...], "implicit":true } ] }
var repo = Path.GetFullPath(args[0]);
var spec = JsonDocument.Parse(File.ReadAllText(args[1])).RootElement;
var projs = new Dictionary<string, JsonElement>();
foreach (var p in spec.GetProperty("projects").EnumerateArray()) projs[p.GetProperty("id").GetString()] = p;

var syms = new List<string> { "NET", "NETCOREAPP", "NET10_0", "NET10_0_OR_GREATER", "NET9_0_OR_GREATER", "NET8_0_OR_GREATER", "NET7_0_OR_GREATER",
  "NET6_0_OR_GREATER", "NET5_0_OR_GREATER", "NETCOREAPP3_1_OR_GREATER", "NETCOREAPP3_0_OR_GREATER", "NETCOREAPP2_1_OR_GREATER",
  "NETSTANDARD2_1_OR_GREATER", "NETSTANDARD2_0_OR_GREATER", "NETSTANDARD1_6_OR_GREATER", "NETSTANDARD1_3_OR_GREATER", "NETSTANDARD1_0_OR_GREATER" };
var popts = new CSharpParseOptions(LanguageVersion.Latest, DocumentationMode.None, SourceCodeKind.Regular, syms);
var refDir = Directory.GetDirectories("/usr/local/share/dotnet/packs/Microsoft.NETCore.App.Ref").OrderBy(x => x).Last() + "/ref/net10.0";
var refs = Directory.GetFiles(refDir, "*.dll").Select(f => (MetadataReference)MetadataReference.CreateFromFile(f)).ToList();

var treeCache = new Dictionary<string, SyntaxTree>();
SyntaxTree Tree(string rel) {
  if (!treeCache.TryGetValue(rel, out var t)) {
    var full = Path.Combine(repo, rel);
    t = CSharpSyntaxTree.ParseText(File.ReadAllText(full), popts, full);
    treeCache[rel] = t;
  }
  return t;
}
IEnumerable<string> Closure(string id) {
  var seen = new HashSet<string> { id }; var q = new Stack<string>(); q.Push(id);
  while (q.Count > 0) { var c = q.Pop(); foreach (var r in projs[c].GetProperty("refs").EnumerateArray().Select(x => x.GetString())) if (projs.ContainsKey(r) && seen.Add(r)) q.Push(r); }
  return seen;
}
var result = new SortedDictionary<string, SortedSet<string>>();
var relOf = new Dictionary<string, string>();
foreach (var p in projs.Values) foreach (var f in p.GetProperty("files").EnumerateArray()) relOf[Path.Combine(repo, f.GetString())] = f.GetString();

foreach (var (id, p) in projs) {
  var own = p.GetProperty("files").EnumerateArray().Select(x => x.GetString()).ToList();
  var all = Closure(id).SelectMany(c => projs[c].GetProperty("files").EnumerateArray().Select(x => x.GetString())).Distinct().ToList();
  var usings = new List<string>();
  if (p.GetProperty("implicit").GetBoolean()) usings.AddRange(new[] { "System", "System.Collections.Generic", "System.IO", "System.Linq", "System.Net.Http", "System.Threading", "System.Threading.Tasks" });
  usings.AddRange(p.GetProperty("usings").EnumerateArray().Select(x => x.GetString()));
  var src = string.Join("\n", usings.Distinct().Select(u => "global using " + u + ";")) + "\n" +
            string.Join("\n", p.GetProperty("staticUsings").EnumerateArray().Select(x => "global using static " + x.GetString() + ";"));
  var gtree = CSharpSyntaxTree.ParseText(src, popts, "/__global_usings.cs");
  var trees = all.Select(Tree).Append(gtree).ToList();
  var comp = CSharpCompilation.Create(id, trees, refs, new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary, allowUnsafe: true));
  foreach (var rel in own) {
    var tree = Tree(rel);
    var model = comp.GetSemanticModel(tree);
    var set = result.TryGetValue(rel, out var s0) ? s0 : (result[rel] = new SortedSet<string>());
    void AddSym(ISymbol sym) {
      if (sym == null) return;
      INamedTypeSymbol t = null;
      switch (sym) {
        case INamedTypeSymbol nt: t = nt; break;
        case IMethodSymbol m: if (m.MethodKind == MethodKind.Constructor || m.IsStatic || m.IsExtensionMethod || m.ReducedFrom != null) t = (m.ReducedFrom ?? m).ContainingType; break;
        case IPropertySymbol or IFieldSymbol or IEventSymbol: if (sym.IsStatic) t = sym.ContainingType; break;
      }
      if (t == null) return;
      t = t.OriginalDefinition;
      foreach (var d in t.DeclaringSyntaxReferences) {
        var fp = d.SyntaxTree.FilePath;
        if (relOf.TryGetValue(fp, out var r) && r != rel) set.Add(r);
      }
    }
    foreach (var node in tree.GetRoot().DescendantNodes()) {
      if (node is IdentifierNameSyntax idn) {
        if (idn.IsVar) continue;
        var info = model.GetSymbolInfo(idn);
        if (info.Symbol != null) AddSym(info.Symbol);
        else foreach (var c in info.CandidateSymbols) AddSym(c);
      } else if (node is GenericNameSyntax gn) {
        var info = model.GetSymbolInfo(gn);
        if (info.Symbol != null) AddSym(info.Symbol);
        else foreach (var c in info.CandidateSymbols) AddSym(c);
      }
    }
  }
}
File.WriteAllText(args[2], JsonSerializer.Serialize(result.ToDictionary(k => k.Key, k => k.Value.ToList())));
