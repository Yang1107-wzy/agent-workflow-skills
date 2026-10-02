"""Synthetic changed utility for a documentation synchronization exercise."""

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--amount", type=int, required=True)
args = parser.parse_args()
if args.amount < 0:
    parser.error("amount must be nonnegative")
print(args.amount * 3)
