"""Map common names to scientific names, ignoring case and extra spaces."""

NAMES = {}

def load(path):
    for line in open(path):
        common, sci = line.rstrip("\n").split("\t")
        NAMES[common.strip().lower()] = sci.strip()

def scientific(common):
    return NAMES.get(" ".join(common.lower().split()))

def test():
    NAMES["tiger"] = "Panthera tigris"
    assert scientific("  Tiger ") == "Panthera tigris"
