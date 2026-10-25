import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.tools.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Parses every .java file with javac (parse only) and prints one JSON line per file:
 *  package, imports, top-level types, all declared type names, type params, identifiers used in
 *  non-method-name position, and maximal qualified-name chains. Usage: JavaScan <repo> <listfile> */
public class JavaScan {
  static String esc(String s){ return "\"" + s.replace("\\","\\\\").replace("\"","\\\"") + "\""; }
  static String arr(Collection<String> c){ StringBuilder b=new StringBuilder("["); boolean f=true; for(String s:new TreeSet<>(c)){ if(!f)b.append(","); f=false; b.append(esc(s)); } return b.append("]").toString(); }
  public static void main(String[] a) throws Exception {
    Path root = Paths.get(a[0]);
    List<String> rel = Files.readAllLines(Paths.get(a[1]));
    JavaCompiler jc = ToolProvider.getSystemJavaCompiler();
    StandardJavaFileManager fm = jc.getStandardFileManager(null, null, java.nio.charset.StandardCharsets.UTF_8);
    PrintStream out = new PrintStream(new FileOutputStream(FileDescriptor.out), false, "UTF-8");
    for (String r : rel) {
      Iterable<? extends JavaFileObject> units = fm.getJavaFileObjects(root.resolve(r).toFile());
      DiagnosticCollector<JavaFileObject> dc = new DiagnosticCollector<>();
      JavacTask t = (JavacTask) jc.getTask(null, fm, dc, List.of("-proc:none","-Xlint:none"), null, units);
      for (CompilationUnitTree cu : t.parse()) {
        String pkg = cu.getPackageName()==null? "" : cu.getPackageName().toString();
        List<String> imps = new ArrayList<>();
        for (ImportTree it : cu.getImports()) imps.add((it.isStatic()?"S ":"N ") + it.getQualifiedIdentifier().toString());
        Set<String> tops = new TreeSet<>(), decls = new TreeSet<>(), tparams = new TreeSet<>(), ids = new TreeSet<>(), chains = new TreeSet<>();
        for (Tree td : cu.getTypeDecls()) if (td instanceof ClassTree) tops.add(((ClassTree)td).getSimpleName().toString());
        new TreePathScanner<Void,Void>() {
          public Void visitClass(ClassTree c, Void p){ if(!c.getSimpleName().isEmpty()) decls.add(c.getSimpleName().toString()); return super.visitClass(c,p);}
          public Void visitTypeParameter(TypeParameterTree c, Void p){ tparams.add(c.getName().toString()); return super.visitTypeParameter(c,p);}
          public Void visitIdentifier(IdentifierTree n, Void p){
            Tree par = getCurrentPath().getParentPath().getLeaf();
            if (par instanceof MethodInvocationTree && ((MethodInvocationTree)par).getMethodSelect()==n) return null;
            ids.add(n.getName().toString()); return null; }
          public Void visitMemberSelect(MemberSelectTree n, Void p){
            Tree par = getCurrentPath().getParentPath().getLeaf();
            if (!(par instanceof MemberSelectTree && ((MemberSelectTree)par).getExpression()==n)) {
              String s = n.toString();
              if (s.matches("[\\w.$]+")) chains.add(s);
            }
            return super.visitMemberSelect(n,p); }
          public Void visitImport(ImportTree n, Void p){ return null; }
          public Void visitPackage(PackageTree n, Void p){ return null; }
        }.scan(cu, null);
        out.println("{\"f\":"+esc(r)+",\"pkg\":"+esc(pkg)+",\"imports\":"+arr(imps)+",\"tops\":"+arr(tops)+",\"decls\":"+arr(decls)+",\"tparams\":"+arr(tparams)+",\"ids\":"+arr(ids)+",\"chains\":"+arr(chains)+",\"errs\":"+dc.getDiagnostics().stream().filter(d->d.getKind()==Diagnostic.Kind.ERROR).count()+"}");
      }
    }
    out.flush();
  }
}
