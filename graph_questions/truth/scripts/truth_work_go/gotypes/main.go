package main

// Same-package file-to-file references via go/types: for every identifier use whose object is declared in
// another file of the same package, emit (user file, declaring file, kind).
import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/build"
	"go/importer"
	"go/parser"
	"go/token"
	"go/types"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type edge struct {
	From, To, Kind string
}

func main() {
	root := os.Args[1]
	ctxt := build.Default
	dirs := map[string]bool{}
	filepath.Walk(root, func(p string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}
		if info.IsDir() && (info.Name() == ".git" || info.Name() == ".aletheore" || info.Name() == "vendor") {
			return filepath.SkipDir
		}
		if !info.IsDir() && strings.HasSuffix(p, ".go") {
			dirs[filepath.Dir(p)] = true
		}
		return nil
	})
	seen := map[edge]bool{}
	var errs int
	for dir := range dirs {
		fset := token.NewFileSet()
		pkgs := map[string][]*ast.File{}
		entries, _ := os.ReadDir(dir)
		for _, e := range entries {
			n := e.Name()
			if e.IsDir() || !strings.HasSuffix(n, ".go") {
				continue
			}
			ok, _ := ctxt.MatchFile(dir, n)
			if !ok {
				continue
			}
			f, err := parser.ParseFile(fset, filepath.Join(dir, n), nil, parser.SkipObjectResolution)
			if err != nil {
				continue
			}
			pkgs[f.Name.Name] = append(pkgs[f.Name.Name], f)
		}
		for name, files := range pkgs {
			if strings.HasSuffix(name, "_test") && len(pkgs) > 1 {
				continue // external test package: cross-package, not same-package
			}
			info := &types.Info{Uses: map[*ast.Ident]types.Object{}, Selections: map[*ast.SelectorExpr]*types.Selection{}}
			conf := types.Config{Importer: importer.ForCompiler(fset, "source", nil), Error: func(error) { errs++ }}
			pkg, _ := conf.Check(name, fset, files, info)
			if pkg == nil {
				continue
			}
			rel := func(pos token.Pos) string {
				r, _ := filepath.Rel(root, fset.Position(pos).Filename)
				return r
			}
			for id, obj := range info.Uses {
				if obj == nil || obj.Pkg() != pkg || !obj.Pos().IsValid() {
					continue
				}
				from, to := rel(id.Pos()), rel(obj.Pos())
				if from == to {
					continue
				}
				kind := "pkglevel"
				if obj.Parent() != pkg.Scope() {
					kind = "member" // method or struct field
				}
				seen[edge{from, to, kind}] = true
			}
		}
	}
	var out []edge
	for e := range seen {
		out = append(out, e)
	}
	sort.Slice(out, func(i, j int) bool { return fmt.Sprint(out[i]) < fmt.Sprint(out[j]) })
	json.NewEncoder(os.Stdout).Encode(out)
	fmt.Fprintln(os.Stderr, "type errors:", errs)
}
