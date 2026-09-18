# Journey

What worldbench is made of, one piece at a time, in plain words. No implementation detail;
that lives in ARCHITECTURE.md. Each entry says what the piece *is*, why it *exists*, and
whether it is built. The "Now" marker shows where we are.

Legend: ✅ built · 🔨 in progress · ⬜ not started

---

## 0. Scaffold ✅
**What it is.** The empty house: folder layout, packaging config, license, the docs that tell
Claude how to work on this repo, and three tiny tests that prove the package installs.
**Why it exists.** So every later session starts from the same, known place and never has to
ask "where does this go?"
**Built.** 2026-09-19. Commit c9a1486.

## 1. Toy refund agent  🔨 Now
**What it is.** A small AI agent (Pydantic AI) that plays customer support for an online shop.
It can look up an order, create a return, and issue a refund, using three hand-written tools
backed by a plain Python dictionary with five fake orders.
**Why it exists.** Not to be part of the product. It is the *patient*: the thing the harness
will be tested against for the next eleven weekends. Building it first means you feel the
problem (an agent that calls tools you cannot control) before building the cure.
**Done when.** You type "return order 3 and refund me" and the dictionary shows a refund.
**Built.** —

## 2. World engine ⬜
**What it is.** The fake world. Reads a `world.yaml` that describes services (orders, payments)
and their records, then builds them in memory with realistic seeded data, fifty orders that
are identical every run. Records can be looked up, changed, and compared before-and-after.
**Why it exists.** An agent needs somewhere to act. Real systems are dangerous to test against
(real refunds); hand-written mocks are weeks of work per project. This turns forty lines of
YAML into a working fake system.
**Done when.** `World.load("shop.yaml").orders.all()` returns fifty orders, the same fifty
every time.
**Built.** —

## 3. MCP server ⬜
**What it is.** The door into the world. Takes the fake services from milestone 2 and exposes
each operation (`get_order`, `issue_refund`) as an MCP tool, the standard way agents call tools.
**Why it exists.** So *any* agent, in any framework, can talk to the fake world without a
line of glue code. The toy agent from milestone 1 should work unchanged when pointed at it.
This is also what makes worldbench framework-neutral, which the big cloud simulators are not.
**Done when.** The toy agent completes a refund against the generated server instead of the dictionary.
**Built.** —

## 4. Fault layer ⬜  ← demo point
**What it is.** The part that makes the world misbehave on purpose: slow responses, timeouts,
errors, rate limits, and a fake clock you can move forward. All controlled by a few lines of
config and reproducible from a seed.
**Why it exists.** This is the whole reason the project exists. Agents fail in production when
the world is slow or broken, and nobody can make a real payments API time out on command.
With this, you can.
**Done when.** Set a 10% timeout rate on refunds and watch the toy agent refund a customer
twice. The bug is reproduced on your laptop. Show someone this the same day.
**Built.** —

## 5. pytest plugin ⬜
**What it is.** The way a developer actually uses all of the above: a normal pytest test that
says "run my agent against this world with these faults, then check the world afterwards."
**Why it exists.** Testing tools that live outside the developer's normal loop get ignored
(that is what killed Distributional). Inside pytest, the harness is one more test file.
**Done when.** The refund test runs green against a fault-free world.
**Built.** —

## 6. Pass rate and trace ⬜
**What it is.** Two things. First, "run this test 20 times and tell me the pass rate" instead of
a single pass/fail, because agents are probabilistic. Second, a recording of every tool call
the agent made, so a failure shows *why* ("timeout, then two successful refunds").
**Why it exists.** This output, "17/20 passed, 3 duplicate refunds after a timeout," is the
product. Everything before it is plumbing to make this line possible.
**Done when.** That line appears, and each failure has a readable trace file.
**Built.** —

## 7. Rules and richer faults ⬜
**What it is.** Business rules written in Python ("returns only within 30 days"), more field
types (dates, enums), and conditional faults ("orders younger than 2 hours are not found yet").
**Why it exists.** Real systems have rules and real failures are conditional. Without this the
fake world is too simple to catch the interesting bugs.
**Done when.** The "ineligible order is not returned" and "sync lag" tests pass or fail for the right reasons.
**Built.** —

## 8. Second framework ⬜
**What it is.** Serving the world over HTTP as well as locally, a `worldbench serve` command,
and a proof that an agent built in a different framework (LangGraph or Mastra) passes the
same tests.
**Why it exists.** "Framework-neutral" is a claim until two frameworks share one world. This
turns it into a fact you can put on the README.
**Done when.** Two frameworks, one world, same tests.
**Built.** —

## 9. Hardening and docs ⬜
**What it is.** Error messages a human can act on, YAML validation that points at the line,
a second example world (calendar + contacts), and user docs for the world file and faults.
**Why it exists.** You have been the only user so far. This is where the tool stops assuming
the reader is you.
**Done when.** One friend writes a world file from the docs alone, and you watch where they get stuck.
**Built.** —

## 10. Release 0.1.0 ⬜
**What it is.** A README that opens with the 20-run demo, a one-minute recording of the bug
being caught, CI on GitHub, and the package on PyPI.
**Why it exists.** `pip install worldbench` working on a stranger's machine is the difference
between a repo and a project.
**Done when.** Clean install, example passes, version 0.1.0 on PyPI.
**Built.** —

## 11. Launch ⬜
**What it is.** Show HN, the MCP and Pydantic AI communities, and a short post telling the
double-refund story.
**Why it exists.** Open source only works if people find it. The story, not the repo link, is
what makes them try it.
**Done when.** Twenty people have tried it and five issues exist that you didn't write.
**Built.** —

## 12. Triage and roadmap ⬜
**What it is.** Fix the top three issues from real users, and publish a roadmap: record/replay
(v0.2), a shareable scenario format (v0.3), hooks for simulated-user tools.
**Why it exists.** This is where you learn which of the whitespace gaps people actually care
about, from their issues rather than your guesses. It is also the first signal of whether this
becomes more than a side project.
**Done when.** Roadmap published; you know what v0.2 is.
**Built.** —

---

## After v0.1 (not planned in detail yet)
- **Record and replay**: save a run, replay it with one thing changed, without paying for LLM calls again.
- **Shared worlds**: a fake Stripe or Salesforce written once, imported by everyone.
- **Fault profiles from real incidents**: postmortems as test fixtures.
