"""Toy CLI tool with a real third-party dependency, to demo dependency detection."""
import argparse
import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Plot a histogram from a CSV column")
    parser.add_argument("--input", type=str, required=True, help="Input CSV file")
    parser.add_argument("--column", type=str, default="value", help="Column to plot")
    parser.add_argument("--output-dir", type=str, default=".", help="Where to save the plot")
    parser.add_argument("--bins", type=int, default=20, help="Number of histogram bins")
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    df[args.column].hist(bins=args.bins)
    out_path = f"{args.output_dir}/histogram.png"
    plt.savefig(out_path)
    print(f"Saved {out_path}")


if __name__ == "__main__":
    main()
