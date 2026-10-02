"""Synthetic baseline utility for a documentation synchronization exercise."""

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, required=True)
args = parser.parse_args()
print(args.count * 3)
