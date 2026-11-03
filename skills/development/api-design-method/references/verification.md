# Verifying the changes

Passing the old tests shows you did not break what they cover. It says nothing about whether the hazard is gone.

## For each change

- **A test that would have failed before.** Show the old misuse now raises, naming the parameter in the expected message. Show valid calls return exactly what they did, compared with values saved before the change.
- **Unchanged results.** For an interface or formatting change, compare outputs before and after on real inputs. Compare the bytes if you can. If they differ, you changed behaviour.
- **Every caller updated.** Search for the old name and old argument across code, tests, documents, examples and records.
- **The project's whole check** at the end of each batch. The latest run is what counts.

## Checks must be able to fail

A check that cannot fail tells you nothing. Introduce the defect on purpose, once, and see the check catch it. Comparing a value with itself, or a relation true by definition, proves nothing.

## Blind trials

Tests cannot tell you whether a stranger can use the API correctly. A blind trial can, and it finds the hazards that scans miss.

1. Give a fresh person or agent a real task and only what a user would have: the package and its documents. Keep out source history, your notes and the reference answer.
2. Compute the reference answer separately, by a route that does not use the library.
3. Compare results. Then read the transcript and the user's own code, not just the answer: where did they guess, misread, convert, or write around the API?
4. Turn each difficulty into a general finding, fix it in the API or documents, not in a note about that task, and try again with a new person if the fix was large.

Good tasks combine several functions and include a convention a careless reader would get wrong.

## Commit messages

Write for someone reading the history later, who was not here.

- The subject says what changed, in the imperative.
- The body says why: the hazard, and what a caller got wrong before.
- It says what callers must now do, if anything.
- It says how this was checked, including what was compared.
- It says what was not done, if a reader might assume otherwise.

The explanation belongs in the message. No separate change file for a refactor.
