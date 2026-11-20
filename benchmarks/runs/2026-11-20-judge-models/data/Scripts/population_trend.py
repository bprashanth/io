"""Fit a log-linear trend to annual counts of red-listed species and flag steep declines."""
import math

RED_LIST = {"Gharial": "CR", "Hoolock gibbon": "EN", "Nilgiri tahr": "EN", "Lion-tailed macaque": "EN"}

def annual_decline(counts):
    """counts: list of (year, n). Returns the yearly % change."""
    xs = [y for y, _ in counts]; ys = [math.log(n) for _, n in counts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return (math.exp(b) - 1) * 100

def flag(species_counts, threshold=-5):
    return {s: round(annual_decline(c), 1) for s, c in species_counts.items()
            if s in RED_LIST and annual_decline(c) < threshold}
