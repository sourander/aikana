# Contributing: iterative SpecDD

This project is developed with [SpecDD](https://specdd.ai). Small `.sdd` spec files sit next to the code they govern.

They are binding contracts for language-model agents, and they are reviewed by humans.

Read `.specdd/bootstrap.md` for the full rules. The essentials are below.

## Where things are

- `aikana.sdd`: root spec with global rules, owned top-level files and the project task list.
- `src/aikana/architecture.sdd`: the Clean Architecture / Ports-and-Adapters contract every feature package follows.
- `src/aikana/aikana.sdd`: governs the `aikana` package directory and lists its feature packages.
- `src/aikana/<feature>/<feature>.sdd`: one spec per feature package (e.g. `courses/courses.sdd`), governing the
  `domain.py`, `ports.py`, `services.py`, `repository_sqlite.py`, `view.py` and `routes.py` it owns.
- `.specdd/bootstrap.project.md`: project rules for agents. `.specdd/bootstrap.local.md` is personal and git-ignored.
- `START_IDEAS.md`: the original notes. They are not a spec and can be deleted once nothing is left to transfer.

## Managing Tasks with AI

Do not write or maintain tasks manually. Instead, use the LLM as your PM and architect.
- **Generate:** Discuss a feature with the agent first, then ask it to write granular `[ ]` steps into the `Tasks` section and claim necessary files in `Owns`.
- **Prune:** `Tasks` are a transient queue, not a permanent history. To prevent context window bloat, periodically ask the agent to delete all `[x]` and `[-]` tasks. Make sure it moves any lasting architectural decisions into the `Must` or `Scenario` rules before deleting.

## The iteration loop

1. **Pick one task.** Choose a `[ ]` item in a spec's `Tasks` section. Prefer the smallest one. (If there are no tasks, ask the agent to generate them).
2. **Plan first when unsure.** Ask the agent for a plan. In planning mode it edits nothing.
3. **Update the spec before the code.** If behavior changes, edit the `Must`, `Scenario` or `Tasks` entries first.
   Specs describe the lasting contract, not the ticket that caused the change.
4. **Ask the agent to do that one task.** Name the spec or path. The agent works only in files that the spec owns or
   may modify, and it stops to ask otherwise.
5. **Test locally in Docker.** Run the app and check the behavior yourself.
6. **Lint the specs.** Run `specdd lint .`.
7. **Close the task.** Mark it `[x]` only after the change and its checks are done. Use `[!]` for blocked work and
   `[?]` for an open decision, and resolve `[?]` items before the code depends on them.
8. **Commit and push when you decide.** Pushing triggers CI/CD to Dokku. Agents must never do this.
9. **Clean up context.** Delete completed `[x]` tasks (or ask the agent to) once they are no longer relevant to current work.

## Task markers

`[ ]` open, `[x]` done, `[-]` skipped, `[!]` blocked, `[?]` needs decision.

## Writing specs

- Keep specs short, local and behavioral. Put a rule in the nearest spec that owns it.
- Every non-`.sdd` file needs an owner. Add a file to `Owns` in its spec before asking for it to be created.
- Do not put `.sdd` files in `Owns` or `Can modify`.
- Write code symbols as `@Symbol` and exact literals in backticks.
- Treat `Must` and `Scenario` sections as permanent memory, and `Tasks` as a temporary to-do list.

## Useful commands

```sh
specdd lint .                       # validate all specs
specdd resolve .                    # show which specs apply to an existing path
specdd inspect .                    # overview of specs and sections
```
