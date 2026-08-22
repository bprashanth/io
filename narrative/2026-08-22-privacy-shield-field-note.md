# Field note: a privacy shield for a product we do not control

The first two stages taught us two uncomfortable things. Participants want
the Antigravity experience — a terse question, a finished dashboard, follow-ups
that keep working — and Antigravity sends whatever it reads to Google. The
local-first ladder could keep data at home but could not match the page. So
the third stage asked a narrower question: can we keep stock Antigravity and
make it blind to the private parts?

The answer turned out to be a proxy, not a model. Antigravity's agent talks
to one backend over plain HTTP JSON, and a local process can sit in between:
replace every name, phone, Aadhaar, account, email and village with a stable
token on the way out, put the real values back on the way in. A 181 MB model
on four CPU threads finds the names the regexes cannot; checksums and formats
catch the identifiers the model would guess at. The participant sees their own
data; the wire carries `NAME_146`.

Getting the IDE to use the proxy was the hard part, and it was learned the
slow way: the IDE reads its backend address at launch, from an internal
setting, and only if the proxy is already listening; an environment variable
alone does nothing; a dead port at startup stalls the window or breaks login;
the daemon must outlive the extension host that started it. Each of those
cost a session, and each is now one line in the extension.

What the shield does not do is as important as what it does. It hides direct
identifiers; it does not make a child unidentifiable from age, village and
school together. It over-hides scheme and school phrases, which the
participant can undo with `don't hide`. It cannot restore a token the model
paraphrased. And it rests on an internal knob that Google can move in any
release, so the status bar refuses to say "active" until a real model call has
passed through, and the smoke suite must be re-run on the build participants
will install.

Measured, in the real IDE, on two machines, with synthetic files shaped like
the ones the survey says participants will bring: dashboards with correct
totals and real values on disk, follow-ups by name, workbooks, chat exports and
PDFs — zero private values on the wire in every probe. That is the layer the
event stack was missing.
