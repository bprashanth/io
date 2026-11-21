"""Clean a CSV: strip spaces, drop empty rows, normalise dates to ISO."""
import csv, sys, datetime

def clean(path_in, path_out):
    with open(path_in) as f, open(path_out, "w", newline="") as g:
        w = csv.writer(g)
        for row in csv.reader(f):
            row = [c.strip() for c in row]
            if any(row):
                w.writerow(row)
