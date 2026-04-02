#!/usr/bin/env python3
"""mock-agent - deterministic agent for E2E tests.

Reads a scenario file mapping task briefs → file operations + results.
The scenario file is a JSON array of entries, each with:
  - match: string to find in the brief (identifies which task this is)
  - operations: [{type: "write", path: "...", content: "..."},
                 {type: "delete", path: "..."}]
  - report_result: {summary: "...", notes: "..."}
  - exit_code: int (default 0)
"""
import sys, json, os

scenario = json.load(open(os.environ["WF_TEST_SCENARIO"]))
brief = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
results_path = os.environ["WF_RESULTS_PATH"]  # where wf expects results.json

for entry in scenario["tasks"]:
    if entry["match"] in brief:
        # Execute scripted file operations in cwd
        for op in entry.get("operations", []):
            if op["type"] == "write":
                os.makedirs(os.path.dirname(op["path"]), exist_ok=True)
                with open(op["path"], "w") as f:
                    f.write(op["content"])
            elif op["type"] == "delete":
                os.remove(op["path"])

        # Write results.json
        results = {
            "exitCode": entry.get("exit_code", 0),
            "messages": [{"role": "assistant", "content": [
                {"type": "toolCall", "name": "report_result",
                 "arguments": entry["report_result"]}
            ]}],
            "usage": {"input": 1000, "output": 500, "cacheRead": 0,
                      "cacheWrite": 0, "cost": 0.01, "turns": 1},
            "model": "mock", "provider": "mock"
        }
        with open(results_path, "w") as f:
            json.dump(results, f)

        sys.exit(entry.get("exit_code", 0))

# No match - simulate agent that didn't understand its task
results = {"exitCode": 1, "messages": [], "usage": {"input": 0, "output": 0,
           "cacheRead": 0, "cacheWrite": 0, "cost": 0, "turns": 0}}
with open(results_path, "w") as f:
    json.dump(results, f)
sys.exit(1)
