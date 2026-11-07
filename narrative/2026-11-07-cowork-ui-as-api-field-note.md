# Seeing what the user sees, on a 30B model

The desktop question had become: which app gives a non-developer the right feel? T3 does best on the
dashboard request. A link in the chat opens a rendered page beside it. Paseo can render the same page,
but the agent prints a path instead of a link, and Paseo blocks the CDN chart library. AionUi works
but routes around the private model when its overrides aren't applied, which rules it out.
[Chronology](../chronology/2026-11-07T1615-laptop-desktop-ux-and-cowork.md).

The more interesting result came from co-work, where the agent works in tabs the user is already
signed into. Paseo's built-in browser tools make this possible. Handing them to Muse as they are does
not work:
- One Gmail page is 8–11k tokens, and two or three of them fill a 65k context.
- Given a shell, the model went looking through the user's home directory, which is the opposite of
  what a privacy product should do.

What worked was a thin adapter that treats the site's page as an API. It knows where Gmail's search
results and message bodies sit and returns only those. It cannot send or edit. With that adapter and
no shell, the same tasks finished in one to two and a half minutes. They had failed before. The model
didn't get smarter; its tools got narrower.

That suggests a division of labour, now the next experiment:
- A frontier model in a "DIY" mode writes and repairs these adapters against test accounts.
- The private model uses them on real accounts, so personal data only ever goes to the private model.

The obvious cost is maintenance whenever a site changes its pages. The planned answer is a test suite
run against the test accounts.

Not shown yet:
- smaller models;
- sites other than Google;
- whether the DIY loop is usable by non-developers;
- anything beyond single runs.
