package decompiler

import (
	"bytes"
	"encoding/json"
	"reflect"
	"testing"
)

func TestInnerThoughtCompileCompatibility(t *testing.T) {
	for _, suffix := range []string{": A private thought.", " [worried]: A private thought."} {
		t.Run(suffix, func(t *testing.T) {
			source := func(channel string) string {
				return "@episode main:01 \"Thought\" {\n" + channel + suffix + "\n@gate { @next main:02 }\n}"
			}
			canonical := compileLS(t, source("INNER_THOUGHT"))
			legacy := compileLS(t, source("YOU"))
			if !bytes.Equal(canonical, legacy) {
				t.Fatalf("new and legacy inputs differ:\n%s\n%s", canonical, legacy)
			}
			var episode map[string]interface{}
			if err := json.Unmarshal(canonical, &episode); err != nil {
				t.Fatal(err)
			}
			steps := episode["steps"].([]interface{})
			thought := steps[len(steps)-1].(map[string]interface{})
			if thought["type"] != "inner_thought" {
				t.Fatalf("thought was emitted as %v", thought)
			}
			if len(steps) == 2 && steps[0].(map[string]interface{})["character"] != "you" {
				t.Fatalf("pose alias changed MC identity: %v", steps[0])
			}
		})
	}
}

func TestInnerThoughtDecompileCompatibility(t *testing.T) {
	canonical := compileLS(t, "@episode main:01 \"Thought\" {\nINNER_THOUGHT: A private thought.\n@gate { @next main:02 }\n}")
	for _, kind := range []string{"inner_thought", "you"} {
		t.Run(kind, func(t *testing.T) {
			input := bytes.ReplaceAll(canonical, []byte(`"inner_thought"`), []byte(`"`+kind+`"`))
			result, err := Decompile(input)
			if err != nil {
				t.Fatal(err)
			}
			source := result.Episodes[0].Source
			if !bytes.Contains(source, []byte("INNER_THOUGHT: A private thought.")) || bytes.Contains(source, []byte("YOU:")) {
				t.Fatalf("noncanonical authoring output: %s", source)
			}
			var want, got interface{}
			json.Unmarshal(canonical, &want)
			json.Unmarshal(compileLS(t, string(source)), &got)
			if !reflect.DeepEqual(want, got) {
				t.Fatalf("round trip changed thought: %v", got)
			}
		})
	}
}
