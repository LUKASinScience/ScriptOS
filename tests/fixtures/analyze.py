"""Toy CLI tool: counts rows in a CSV above a threshold value in a given column."""
import argparse
import csv
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="Analyze a CSV file")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file")
    parser.add_argument("--column", type=str, default="value", help="Column to threshold on")
    parser.add_argument("--threshold", type=float, default=0.05, help="Significance threshold")
    parser.add_argument("--threads", type=int, default=4, help="CPU threads (unused, for UI demo)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print(f"Loading input: {args.input}")
    with open(args.input, newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"Processing {len(rows)} records")

    count = 0
    for row in rows:
        value = float(row[args.column])
        if args.verbose:
            print(f"  row value={value}")
        time.sleep(0.05)
        if value > args.threshold:
            count += 1

    print(f"{count} of {len(rows)} rows above threshold {args.threshold}")
    print("Done.")
    sys.exit(0)


if __name__ == "__main__":
    main()
