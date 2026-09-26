package main

import (
	"fmt"
	"os"
	"strings"
)

// --- 010: gin-runfd-file-leak ---
// old had `defer f.Close()`; new removed it. Neither RETURN VALUE differs -
// this is a pure resource-lifecycle bug, invisible to any test that only
// compares outputs. Checked here by inspecting whether the fd is actually
// closed afterward (Fd() on a closed *os.File still returns the same
// uintptr, so the real signal is whether a subsequent syscall on it fails).
func runFd_old(fd int) *os.File {
	f := os.NewFile(uintptr(fd), fmt.Sprintf("fd@%d", fd))
	defer f.Close()
	return f // returned only so the caller can check its closed-ness for this harness
}

func runFd_new(fd int) *os.File {
	f := os.NewFile(uintptr(fd), fmt.Sprintf("fd@%d", fd))
	return f
}

func isClosed(f *os.File) bool {
	_, err := f.Stat()
	return err != nil
}

func test010() (string, string) {
	r, w, _ := os.Pipe()
	defer r.Close()
	oldF := runFd_old(int(w.Fd()))
	oldClosed := isClosed(oldF)

	r2, w2, _ := os.Pipe()
	defer r2.Close()
	newF := runFd_new(int(w2.Fd()))
	newClosed := isClosed(newF)
	if !newClosed {
		w2.Close()
	}

	if oldClosed == newClosed {
		return "IDENTICAL", "(return-value differential testing alone would report IDENTICAL here too - the leak is invisible to it; explicit resource-lifecycle check is what catches it)"
	}
	return "DIVERGED", fmt.Sprintf("old closes fd on return=%v, new closes fd on return=%v (real leak)", oldClosed, newClosed)
}

// --- 012: urfave-cli-empty-positional-arg ---
func parsePositional_old(args []string) (posArgs []string, stoppedEarly bool) {
	for _, raw := range args {
		firstArg := strings.TrimSpace(raw)
		if len(firstArg) == 0 {
			posArgs = append(posArgs, raw)
			continue
		}
		if raw == "--" {
			break
		}
		posArgs = append(posArgs, raw)
	}
	return posArgs, false
}

func parsePositional_new(args []string) (posArgs []string, stoppedEarly bool) {
	for _, raw := range args {
		firstArg := strings.TrimSpace(raw)
		if len(firstArg) == 0 {
			break
		}
		if raw == "--" {
			break
		}
		posArgs = append(posArgs, raw)
	}
	return posArgs, false
}

func test012() (string, string) {
	// A positional arg list with a genuinely empty string in the middle -
	// e.g. a shell-quoted "" passed as a real positional argument.
	args := []string{"first", "", "third"}
	oldPos, _ := parsePositional_old(args)
	newPos, _ := parsePositional_new(args)
	oldStr := strings.Join(oldPos, ",")
	newStr := strings.Join(newPos, ",")
	if oldStr != newStr {
		return "DIVERGED", fmt.Sprintf("args=%v old_posArgs=%q new_posArgs=%q (new silently drops \"third\")", args, oldStr, newStr)
	}
	return "IDENTICAL", ""
}

func main() {
	s010, d010 := test010()
	s012, d012 := test012()
	fmt.Printf("%-45s %-10s %s\n", "010-gin-runfd-file-leak", s010, d010)
	fmt.Printf("%-45s %-10s %s\n", "012-urfave-cli-empty-positional-arg", s012, d012)
}
