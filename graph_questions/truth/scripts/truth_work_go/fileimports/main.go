package main

import (
	"encoding/json"
	"fmt"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: fileimports <repository-root>")
		os.Exit(2)
	}
	root := os.Args[1]
	out := map[string]map[string]interface{}{}
	if err := filepath.Walk(root, func(p string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() && (info.Name() == ".git" || info.Name() == ".aletheore" || info.Name() == "vendor") {
			return filepath.SkipDir
		}
		if info.IsDir() || !strings.HasSuffix(p, ".go") {
			return nil
		}
		fs := token.NewFileSet()
		f, err := parser.ParseFile(fs, p, nil, parser.ImportsOnly)
		if err != nil {
			return nil
		}
		rel, _ := filepath.Rel(root, p)
		var imps []string
		for _, i := range f.Imports {
			s, _ := strconv.Unquote(i.Path.Value)
			imps = append(imps, s)
		}
		out[rel] = map[string]interface{}{"pkg": f.Name.Name, "imports": imps}
		return nil
	}); err != nil {
		fmt.Fprintln(os.Stderr, "walk repository:", err)
		os.Exit(1)
	}
	json.NewEncoder(os.Stdout).Encode(out)
}
