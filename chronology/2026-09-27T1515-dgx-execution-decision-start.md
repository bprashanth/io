# Local/remote decision experiment begins

Owner requested a staged architecture decision experiment: investigate pinned
Windows elevated error 5, evaluate newer/MXC behavior without weakening the contract,
then ordinary-user/desktop coverage and a runtime smoke check if justified.
[Proposal](../proposals/local-remote-execution-decision.md) fills the stages and gates.

Available here: DGX Linux, public Codex source/packages and GitHub Windows Server CI.
Not available here: Windows 11 24H2/25H2 or ordinary physical Windows laptop. Asked
owner about a later laptop run while continuing independent CI work. A hosted
server or non-admin CI account will not be called a Windows 11 test.

Prior evidence: Linux with explicit AppArmor setup and both Mac CI targets passed.
Windows unelevated rejected restricted reads; a separately weakened-read diagnostic
proved raw TCP escaped its Offline policy. Elevated exact-policy Open passed;
Offline failed CreateProcessAsUserW with error 5. No backend change is in the app.

Investigating the source before choosing candidates: latest release resolves to
0.157.1; 0.154.0 already contains MXC-related source, so a changelog entry alone
cannot establish that the CLI can select it. Cursor CLI gpt-5.4-mini-high is doing
a read-only source comparison. Product package pins and remote deployment stay put.

Startup smoke packaging is gated on successful backend evidence. Existing wallProbe
is not the full network/child/traversal suite. Remote fallback must remain explicit
about upload/privacy/price; local ChatGPT use still needs model connectivity.
