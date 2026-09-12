"""Workflow demo, step 2: reads step 1's output directory and uses its result."""
import argparse
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("--input-dir", type=str, default=".", help="Directory containing step 1's output")
args = parser.parse_args()

value = pathlib.Path(args.input_dir, "step_a_result.txt").read_text().strip()
print(f"step_b read: {value}, doubled: {int(value) * 2}")
