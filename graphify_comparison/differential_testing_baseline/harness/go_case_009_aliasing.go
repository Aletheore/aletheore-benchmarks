package main

import "fmt"

func trimAndAppend_old(args []string) []string {
	trimmedArgs := make([]string, len(args)-1)
	copy(trimmedArgs, args[:len(args)-1])
	return append(trimmedArgs, "--")
}

func trimAndAppend_new(args []string) []string {
	trimmedArgs := args[:len(args)-1]
	return append(trimmedArgs, "--")
}

func testCorruption(fn func([]string) []string) (corrupted bool, valAfter string) {
	// args has len=3 ("cmd","sub","flag") but spare capacity 6, exactly the
	// shape a re-sliced os.Args-derived value has in a real process.
	backing := make([]string, 3, 6)
	backing[0], backing[1], backing[2] = "cmd", "sub", "flag"
	args := backing // len=3, cap=6

	before := args[2] // "flag" - the caller's own last positional arg
	_ = fn(args)
	after := args[2]
	return before != after, after
}

func main() {
	oldCorrupted, _ := testCorruption(trimAndAppend_old)
	newCorrupted, newVal := testCorruption(trimAndAppend_new)

	if oldCorrupted != newCorrupted {
		fmt.Printf("DIVERGED\told corrupts caller's args[2]=%v new corrupts caller's args[2]=%v (args[2] after new call=%q, was %q)\n",
			oldCorrupted, newCorrupted, newVal, "flag")
	} else {
		fmt.Println("IDENTICAL\t")
	}
}
