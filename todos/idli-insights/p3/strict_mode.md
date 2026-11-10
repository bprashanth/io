# Strict mode: flag everything

Owner's decision, 2026-11-10: by default Idli quietly reads values that are right but written inconsistently ("Rs.
1,200", "approx 12", mixed date formats, casing, "n/a"). It flags them only when the inconsistency would confuse
the 9B, for example two spellings of one village that would split a count. Fewer flags are less intimidating.

Later, add a strict mode the person can turn on (a card when cleaning: "Flag every inconsistency, even ones Idli can
read?"). It marks every such value in the working copy, grouped as one comment per kind, for teams that want a
fully standardised sheet. The checks already know these values (fixkit suggests fixes for them), so this is
mostly about showing them.
