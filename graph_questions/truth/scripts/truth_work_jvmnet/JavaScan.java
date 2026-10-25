import com.sun.source.tree.ClassTree;
import com.sun.source.tree.CompilationUnitTree;
import com.sun.source.tree.IdentifierTree;
import com.sun.source.tree.ImportTree;
import com.sun.source.tree.MemberSelectTree;
import com.sun.source.tree.MethodInvocationTree;
import com.sun.source.tree.PackageTree;
import com.sun.source.tree.Tree;
import com.sun.source.tree.TypeParameterTree;
import com.sun.source.util.JavacTask;
import com.sun.source.util.TreePathScanner;
import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.TreeSet;
import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;

/** Parses Java sources and prints one JSON line per file. */
public class JavaScan {
  static String esc(String value) {
    return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
  }

  static String arr(Collection<String> values) {
    StringBuilder result = new StringBuilder("[");
    boolean first = true;
    for (String value : new TreeSet<>(values)) {
      if (!first) {
        result.append(",");
      }
      first = false;
      result.append(esc(value));
    }
    return result.append("]").toString();
  }

  public static void main(String[] args) throws Exception {
    Path root = Paths.get(args[0]);
    List<String> relativePaths = Files.readAllLines(Paths.get(args[1]));
    JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
    if (compiler == null) {
      throw new IllegalStateException("A JDK with the system Java compiler is required");
    }

    try (StandardJavaFileManager fileManager =
            compiler.getStandardFileManager(null, null, StandardCharsets.UTF_8);
        PrintStream out =
            new PrintStream(new FileOutputStream(FileDescriptor.out), false, StandardCharsets.UTF_8)) {
      for (String relativePath : relativePaths) {
        Iterable<? extends JavaFileObject> units =
            fileManager.getJavaFileObjects(root.resolve(relativePath).toFile());
        DiagnosticCollector<JavaFileObject> diagnostics = new DiagnosticCollector<>();
        JavacTask task =
            (JavacTask)
                compiler.getTask(
                    null, fileManager, diagnostics, List.of("-proc:none", "-Xlint:none"), null, units);
        for (CompilationUnitTree unit : task.parse()) {
          String packageName = unit.getPackageName() == null ? "" : unit.getPackageName().toString();
          List<String> imports = new ArrayList<>();
          for (ImportTree item : unit.getImports()) {
            imports.add((item.isStatic() ? "S " : "N ") + item.getQualifiedIdentifier());
          }
          TreeSet<String> topLevel = new TreeSet<>();
          TreeSet<String> declarations = new TreeSet<>();
          TreeSet<String> typeParameters = new TreeSet<>();
          TreeSet<String> identifiers = new TreeSet<>();
          TreeSet<String> chains = new TreeSet<>();
          for (Tree declaration : unit.getTypeDecls()) {
            if (declaration instanceof ClassTree classTree) {
              topLevel.add(classTree.getSimpleName().toString());
            }
          }
          new TreePathScanner<Void, Void>() {
            @Override
            public Void visitClass(ClassTree tree, Void unused) {
              if (!tree.getSimpleName().isEmpty()) {
                declarations.add(tree.getSimpleName().toString());
              }
              return super.visitClass(tree, unused);
            }

            @Override
            public Void visitTypeParameter(TypeParameterTree tree, Void unused) {
              typeParameters.add(tree.getName().toString());
              return super.visitTypeParameter(tree, unused);
            }

            @Override
            public Void visitIdentifier(IdentifierTree tree, Void unused) {
              Tree parent = getCurrentPath().getParentPath().getLeaf();
              if (parent instanceof MethodInvocationTree invocation
                  && invocation.getMethodSelect().equals(tree)) {
                return null;
              }
              identifiers.add(tree.getName().toString());
              return null;
            }

            @Override
            public Void visitMemberSelect(MemberSelectTree tree, Void unused) {
              Tree parent = getCurrentPath().getParentPath().getLeaf();
              if (!(parent instanceof MemberSelectTree selection
                  && selection.getExpression().equals(tree))) {
                String value = tree.toString();
                if (value.matches("[\\w.$]+")) {
                  chains.add(value);
                }
              }
              return super.visitMemberSelect(tree, unused);
            }

            @Override
            public Void visitImport(ImportTree tree, Void unused) {
              return null;
            }

            @Override
            public Void visitPackage(PackageTree tree, Void unused) {
              return null;
            }
          }.scan(unit, null);
          long errors =
              diagnostics.getDiagnostics().stream()
                  .filter(diagnostic -> diagnostic.getKind() == Diagnostic.Kind.ERROR)
                  .count();
          out.println(
              "{\"f\":"
                  + esc(relativePath)
                  + ",\"pkg\":"
                  + esc(packageName)
                  + ",\"imports\":"
                  + arr(imports)
                  + ",\"tops\":"
                  + arr(topLevel)
                  + ",\"decls\":"
                  + arr(declarations)
                  + ",\"tparams\":"
                  + arr(typeParameters)
                  + ",\"ids\":"
                  + arr(identifiers)
                  + ",\"chains\":"
                  + arr(chains)
                  + ",\"errs\":"
                  + errors
                  + "}");
        }
      }
      out.flush();
    }
  }
}
