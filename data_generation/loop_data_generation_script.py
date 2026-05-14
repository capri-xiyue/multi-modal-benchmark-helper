import argparse
import json
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Run data_generation_script.py in a loop with different configs.")
    parser.add_argument("--config_file", type=str, required=True, help="Path to JSON file containing list of configs.")
    args = parser.parse_args()

    if not os.path.exists(args.config_file):
        print(f"Error: Config file {args.config_file} not found.")
        sys.exit(1)

    with open(args.config_file, "r") as f:
        try:
            configs = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            sys.exit(1)

    if not isinstance(configs, list):
        print("Error: Config file must contain a list of configurations.")
        sys.exit(1)

    script_path = os.path.join(os.path.dirname(__file__), "data_generation_script.py")

    for i, config in enumerate(configs):
        print(f"\n=== Running config {i+1}/{len(configs)} ===")
        print(json.dumps(config, indent=2))

        cmd = ["python3", script_path]
        
        for key, value in config.items():
            if isinstance(value, list):
                cmd.append(f"--{key}")
                cmd.extend([str(v) for v in value])
            elif isinstance(value, bool):
                if value:
                    cmd.append(f"--{key}")
                # If false, assuming we don't pass it (flag style)
            else:
                cmd.append(f"--{key}")
                cmd.append(str(value))

        print(f"Executing: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            print(f"=== Config {i+1} completed successfully ===\n")
        except subprocess.CalledProcessError as e:
            print(f"Error running config {i+1}: {e}")
            print("Continuing with next config...\n")

if __name__ == "__main__":
    main()
