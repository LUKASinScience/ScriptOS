"""Workflow demo, step 1: writes a small result file for step 2 to pick up."""
import argparse
import pathlib

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", type=str, default=".", help="Where to write results")
args = parser.parse_args()

pathlib.Path(args.output_dir, "step_a_result.txt").write_text("42\n")
print("wrote step_a_result.txt")
