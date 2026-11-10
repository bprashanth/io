# The tax end-before-start "regression" in E1 (fixed copy)

Owner's decision 2 asked for this to be checked before the fixed copy is called good.

**What happened:** in the today copy, the tax fake's "sale before purchase" mistake survived, and in the fixed copy it
didn't. But neither version keeps the link between the two dates:
- The sale date column ("12-Mar-22" style, dd-mmm-yy) isn't recognised as a date (`filekit.classify` says
  category). Its fake values are drawn at random.
- The purchase date column in the fixture is a single repeated value.
- So whether a fake sale lands before the purchase is a coin toss. Across seeds 1-5 the outcome flips in both
  versions. The fix only changed which random numbers were drawn, not this logic.

**Verdict:** not a regression from the fix; it was random in both. Two real gaps remain, and both are noted for
later:
- dd-mmm-yy dates aren't read as dates;
- the fake copy doesn't keep the order between two date columns (start before end).
