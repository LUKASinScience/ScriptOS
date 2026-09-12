import argparse
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, required=True, help="Input CSV file")
parser.add_argument("--threshold", type=float, default=0.05, help="Significance threshold")
parser.add_argument("--threads", type=int, default=4, help="CPU threads")
parser.add_argument("--output-dir", type=str, default=".", help="Where to write results")
parser.add_argument("--verbose", action="store_true", help="Verbose output")
args = parser.parse_args()
