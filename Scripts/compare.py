"""Rotate candidates across runs and retain sample logs and medians."""
import argparse
import csv
import hashlib
import re
import statistics
from pathlib import Path

from device import ROOT
from run import run


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", type=Path)
    ap.add_argument("--runs", type=int, default=3)
    args = ap.parse_args()
    args.results.mkdir(parents=True, exist_ok=False)
    names = ["gcc7", "gcc9", "zig"]
    samples = {name: [] for name in names}
    reference = None
    for i in range(args.runs):
        offset = i % len(names)
        for name in names[offset:] + names[:offset]:
            binary = ROOT / "build" / name / "bench"
            log = args.results / f"{name}-{i+1}.log"
            run(binary, log)
            match = re.search(r"(checksum=\w+ byte=\d+ pixel=\w+) cpu_ms=([.\d]+) copy_MiB_s=([.\d]+) blits_s=([.\d]+)", log.read_text())
            if not match or match[1] != (reference or match[1]):
                raise ValueError("Результаты вычисления различаются")
            reference = match[1]
            samples[name].append(tuple(map(float, match.groups()[1:])))
    with (args.results / "medians.tsv").open("w") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["tool", "bytes", "sha256", "runs", "cpu_ms", "copy_MiB_s", "blits_s"])
        for name, rows in samples.items():
            data = (ROOT / "build" / name / "bench").read_bytes()
            writer.writerow([name, len(data), hashlib.sha256(data).hexdigest(), len(rows),
                             *map(statistics.median, zip(*rows))])


if __name__ == "__main__":
    main()
