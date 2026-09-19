# Journey

What we are building, one piece at a time, in plain words. For Mithun to read.
Each piece: what it is, why we need it, and whether it's done.

✅ done · 🔨 doing now · ⬜ not yet

---

### 0. Scaffold ✅
**What:** The empty project: folders, config, license, and the notes that tell Claude how to work here.
**Why:** So every work session starts from the same place.
**Built:** 19 Sep. The repo exists and installs.

### 1. Toy refund agent ✅
**What:** A small AI support agent for a fake shop. It can look up an order, create a return, and issue a refund.
**Why:** It's the *patient*. Everything we build next is for testing agents like this one. We build it first so we feel the problem before building the cure.
**Built:** 19 Sep. Ran live on gpt-5-mini. It works, and it even refuses to refund an already-returned order. Lesson learned: a decent agent doesn't break on its own; we'll need to *make* things fail (piece 4) to see the double-refund bug.

### 2. World engine ✅
**What:** The fake world. You describe your services (orders, payments) in a short YAML file; it creates them in memory with 50 realistic fake orders, the same 50 every time.
**Why:** Agents need somewhere safe to act. Real systems are dangerous to test on (real refunds). Hand-made fakes take weeks. This makes one from 40 lines of YAML.
**Built:** 19 Sep. Loading the same file always gives byte-identical data, checked across separate runs. 36 tests.

### 3. MCP server ✅
**What:** The door into the fake world. Turns each operation (get order, issue refund) into a tool the agent can call, using MCP, the standard way agents talk to tools.
**Why:** So *any* agent, built with any framework, can use the fake world with zero glue code. The toy agent from piece 1 should work unchanged when pointed at it.
**Built:** 19 Sep. The shop's tools are now generated from the YAML file, not hand-written. The toy agent, unchanged, returned an order and refunded it against the generated world. The hand-written server from piece 1 is gone.

### 4. Fault layer ✅  ← the big demo
**What:** Makes the world misbehave on purpose: slow replies, timeouts, errors, and a fake clock you can move forward. (Rate limits and conditional faults come with piece 7.)
**Why:** This is the whole point of the project. Agents fail in production when the world is slow or broken, and nobody can make a real payments API time out on command. Now you can.
**Built:** 19 Sep. With faults on, `issue_refund` times out 10% of the time — after the refund already went through. Run live, the agent saw the timeout, retried, and **refunded the customer twice**. The exact production bug, reproduced on demand and flagged automatically.

### 5. pytest plugin ✅
**What:** Lets a developer use all of the above as a normal test: "run my agent against this world with these faults, then check what happened."
**Why:** Testing tools that live outside a developer's normal workflow get ignored. Inside pytest, it's just one more test file.
**Built:** 19 Sep. A test tags itself with `@pytest.mark.world("shop.yaml")` and asks for `world` and `mcp_server`; the plugin builds them and cleans up. The real refund test now reads like an ordinary pytest test and passes green against a fault-free world.

### 6. Pass rate and trace ✅
**What:** Run a test many times and report a pass rate, plus a recording of every tool call so a failure shows *why*.
**Why:** Agents are random; a single pass/fail lies. The line "17/20 passed, 3 duplicate refunds after a timeout" *is* the product. Everything before this exists to make that line possible.
**Built:** 19 Sep. Running the refund test 6 times under a 20% timeout printed `5/6 passed (83%)` and, for the failing run, the trace `get_order → create_return → issue_refund!timeout → issue_refund` — the double refund, caught and explained. `min_pass_rate` turns the rate into a CI pass/fail.

### 7. Rules and smarter faults ✅
**What:** Business rules in Python ("returns only within 30 days"), dates and enums, and faults that depend on conditions ("orders younger than 2 hours aren't found yet") plus rate limits.
**Why:** Real systems have rules and real failures are conditional. Without this the fake world is too simple to catch interesting bugs.
**Built:** 19 Sep. The fake clock now drives real rules: a delivered order is refundable only within 30 days (move the clock forward and it's refused), a just-placed order isn't visible yet (sync lag), and too many calls in a window get rate-limited — all deterministic and testable without waiting.

### 8. Second framework ✅
**What:** Serve the world over HTTP, a `faultbench serve` command, and prove a *different* MCP client — not the one the agent uses — drives the same world.
**Why:** "Works with any framework" is a claim until something other than Pydantic AI talks to the world. Then it's a fact for the README.
**Built:** 19 Sep. `faultbench serve --http` puts the world on a URL, and the reference MCP client connects to it, calls the tools, and changes the world — no Pydantic AI involved. Any MCP-speaking framework connects the same way.
**Validated (during release):** a real second agent framework — the OpenAI Agents SDK — drove the same world over HTTP. Fault-free it refunded cleanly; with a forced timeout it retried and refunded the customer *three times* while telling them it had failed — and faultbench caught it. Testing this before launch also flushed out a genuine faultbench bug (faulted writes weren't being mirrored to out-of-process readers), now fixed.

### 9. Polish and docs ✅
**What:** Clear error messages on bad world files, a second example world, and user docs.
**Why:** You've been the only user. This is where the tool stops assuming the reader is you.
**Built:** 19 Sep. Two guides — "write a world" and "test an agent" — plus a second, different
world (a tiny bank) that a reader can copy from. Bad world files now fail with a message that
names the problem instead of a stack trace.

### 10. Release 0.1.0 🔨 now
**What:** README that opens with the 20-run demo, a one-minute recording, CI, and the package on PyPI.
**Why:** `pip install faultbench` working on a stranger's machine is the difference between a repo and a project.
**So far (19 Sep):** a one-line helper so the first test is copy-paste (`run_agent(model, prompt, mcp=...)`), the README demo is now the real runnable one, CI is written, and the 0.1.0 wheel builds and installs clean in a fresh environment. Still to do, and held for you: pushing to GitHub (new account) and publishing to PyPI — the irreversible steps.

### 11. Launch ⬜
**What:** Show HN, the MCP and Pydantic AI communities, a short post telling the double-refund story.
**Why:** Open source only works if people find it. The story, not the link, makes them try it.
**Done when:** 20 people tried it; 5 issues you didn't write.

### 12. Listen and plan ⬜
**What:** Fix the top three issues from real users; publish what v0.2 will be.
**Why:** First time you learn what people actually want, from their issues instead of your guesses. Also the first signal of whether this becomes more than a side project.

---

### Later, if it goes well
- **Record and replay:** save a run, replay it with one change, no LLM cost.
- **Shared worlds:** a fake Stripe or Salesforce written once, used by everyone.
- **Faults from real outages:** postmortems turned into test cases.
