# Field note: what the wall is for, and what it kept breaking instead

io makes one promise that is easy to say and hard to keep: your files stay yours. The proxy
keeps the half of it that everybody thinks of first, turning names and phone numbers into
codes before anything reaches a model. The wall keeps the other half, and the other half is
where a day of testing on a real laptop went.

The wall is a sandbox around the commands the assistant runs. It is not the same mechanism
as the tokeniser and it does not defend against the same thing. The tokeniser assumes the
model provider is the risk. The wall assumes the assistant itself is: that a command it runs
could read the folder next door, or post a file somewhere, and that neither of those needs
malice to happen. This distinction is not academic. Almost every confusion we hit came from
somebody, including us, attributing one mechanism's behaviour to the other.

## The wall was blocking the wrong thing

The first thing the laptop taught us is that the wall's privacy value and its practical cost
sit in different places. Its value is that it refuses the home directory. Its cost, in
practice, was that the only pandas on the machine *was* in the home directory, as a per-user
install, so `import pandas` failed inside the wall while succeeding everywhere else. The
assistant, denied the library, did what a capable model does when a tool is missing: it
improvised. It unzipped the spreadsheet and walked the XML by hand, failed on a missing
shared-strings table, retried four times and produced a partial answer. To the person
watching, a privacy feature looked like a broken app, and the failure was about file formats
rather than their question.

The fix was small and the lesson was not. io ships its own Python with pandas, numpy and
openpyxl; granting the wall read access to it and putting it first on the assistant's PATH
took a few lines. The lesson is that a sandbox needs a toolbox packed for it deliberately.
Whatever you do not pack, the model will improvise around, and its improvisations are worse
than the libraries it was denied. A wall with nothing inside it does not produce caution. It
produces an assistant reinventing openpyxl badly.

## The way out was the browser, not the network

We spent a while assuming network access was the boundary that mattered, and it is not the
one that leaks. The assistant writes a chart or a report as a self-contained HTML file. The
person opens it. That file is arbitrary JavaScript with full network in the person's own
browser, running outside the proxy and outside the wall, carrying whatever data was inlined
when it was written. We demonstrated it against a listener on loopback: a page of exactly
the kind the assistant produces sent real names, phone numbers and GPS coordinates out of
the browser while the footer still said Protected.

Chrome does block such a page from reading a sibling CSV, which sounds like a mitigation and
is not, because the data does not need to be read at runtime. It is already in the file. A
genuine dashboard works the same way.

So "may io open a page for you" turned out to belong in the privacy settings alongside "may
commands reach the internet", which is not where anyone would have put it at the start. The
strictest setting now declines to open pages at all, and that is the honest meaning of the
word offline.

## A label is not a fact until you try to break it

The setting screen was nearly shipped with a hole underneath it. Codex's default approval
policy lets the model ask the person to run a command outside the sandbox. We had watched it
do exactly that, politely, when it wanted to open a map. A person clicking yes to that
prompt gets a command with the whole machine and the whole network, whatever setting they
picked. Offline would have been a word on a card.

Turning that off is one flag. What it cost was instructive: with approvals off, the
assistant also cannot call a tool. The lock on escalation and the channel for tools are the
same switch. Which means the strictest setting cannot have tools, by construction — and
that is a fact worth printing on the card rather than an inconvenience to work around.

## The tool channel existed already

The remaining question was how a vetted tool would reach out on the person's behalf when the
assistant itself may not. We assumed a broker would have to be built. It did not.

A local tool server registered with the assistant runs *outside* the command sandbox. In a
folder session with networking switched off, a shell command asking for a loopback address
failed with a connection error, while a tool on a server io had registered reached the same
address and said so. That contrast is the whole architecture: the assistant stays walled,
the vetted tool does the reaching, and the boundary is a process boundary rather than a
promise. The approval prompt for such a tool already offers "always allow", per tool, which
is the install gesture an app store needs.

## What the day actually argues

Three things, none of which we would have found by reading the code.

A sandbox is a product surface, not a security control you can bolt on quietly. Every one of
its refusals becomes something the person sees, usually mis-attributed, usually at the worst
moment. It has to be packed, explained and named in their words.

The dangerous edge is rarely the one being guarded. Network access was guarded carefully.
The HTML file the person double-clicks was not, and it is the wider channel by a distance.

And a privacy setting is only true once someone has tried to defeat it from the inside. Both
of the real holes found today — the escalation prompt and the browser — were reachable
without any adversary at all, by an assistant being helpful and a person clicking yes.

Evidence for all of it is in `../chronology/2026-09-15T*-laptop-*.md`, with screenshots
under `../benchmarks/runs/2026-09-15-laptop/`.
