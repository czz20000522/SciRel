# Planning the changes

## Rank by harm

| Priority | Kind | Examples |
| --- | --- | --- |
| 1 | Wrong results without warning | Ignored input, hidden default, silent clamp, unit ambiguity |
| 2 | Documentation that misleads | Wrong formula variant, stale example, contradiction between copies |
| 3 | Things that are hard to use correctly | Mapping parameters, opaque selectors, duplicate entry points |
| 4 | Inconsistency | Names, return shapes, section coverage |
| 5 | Appearance | Formatting, layout |

Within a level, do first what the most callers reach, then what costs least. Work that callers of a demonstration or release depend on comes first of all.

## Choose the smallest change that removes the hazard

- Raising an error at the entrance is usually smaller and safer than a redesign.
- Making an argument required removes a hidden default with one line.
- Documenting a convention fixes the hazard if the behaviour is right.
- Rename or move only when the current name causes real mistakes or the release window is closing.

If you changed a function's result to remove a hazard, it was not an interface change. Separate it and get a decision.

## Batches

- One concern per batch. Mechanical formatting and renaming are separate from behaviour.
- Each batch leaves the project's checks passing.
- For a rename, change the code, tests, documents and records together, and search for the old name afterwards.
- Order batches so that a stopped effort still leaves the library better.

## Handing work over

Keep the decisions yourself. Hand over what is mechanical once it has been shown on a few representative functions. A good task states:

- what to change, and the method, linked to the standard;
- the exact scope, or how to compute it;
- the command that shows it is done;
- what not to change, especially results;
- when to stop and ask.

One task covers one kind of change, in a size one reviewer can check.

## When to stop

Stop when any of these is true:

- Every known priority 1 and 2 finding is fixed, or written down with a reason.
- The next change would break more callers than it would help.
- The remaining findings are matters of taste.
- A change would need a decision that belongs to someone else. Write the question down with your recommendation and go on to other work.
- You have started to change results, or to redesign things nobody has had trouble with.

Finish by listing what remains and what you would do next.
