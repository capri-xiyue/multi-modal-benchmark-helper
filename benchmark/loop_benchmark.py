import argparse
import json
import subprocess
import sys
import os
import time

def main():
    parser = argparse.ArgumentParser(description="Run benchmark.py in a loop with different configs.")
    parser.add_argument("--config_file", type=str, required=True, help="Path to JSON file containing list of configs.")
    args = parser.parse_args()

    if not os.path.exists(args.config_file):
        print(f"Error: Config file {args.config_file} not found.", flush=True)
        sys.exit(1)

    with open(args.config_file, "r") as f:
        try:
            configs = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}", flush=True)
            sys.exit(1)

    if not isinstance(configs, list):
        print("Error: Config file must contain a list of configurations.", flush=True)
        sys.exit(1)

    script_path = os.path.join(os.path.dirname(__file__), "benchmark.py")

    for i, config in enumerate(configs):
        print(f"\n=== Running benchmark config {i+1}/{len(configs)} ===", flush=True)
        print(json.dumps(config, indent=2), flush=True)

        cmd = ["python3", script_path]
        
        for key, value in config.items():
            # Convert underscores to hyphens for benchmark.py arguments
            flag_key = key.replace('_', '-')
            
            if isinstance(value, list):
                cmd.append(f"--{flag_key}")
                cmd.extend([str(v) for v in value])
            elif isinstance(value, bool):
                if value:
                    cmd.append(f"--{flag_key}")
            else:
                cmd.append(f"--{flag_key}")
                cmd.append(str(value))

        print(f"Executing: {' '.join(cmd)}", flush=True)
        try:
            # Set PYTHONUNBUFFERED to ensure child process output is flushed immediately
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            
            subprocess.run(cmd, check=True, env=env)
            print(f"=== Benchmark config {i+1} completed successfully ===\n", flush=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running benchmark config {i+1}: {e}", flush=True)
            print("Continuing with next config...\n", flush=True)

        if i < len(configs) - 1:
            print("Resting for 3 minutes before next stage...", flush=True)
            time.sleep(180)

if __name__ == "__main__":
    main()
