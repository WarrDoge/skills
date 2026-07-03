---
name: functional-simplicity
description: Separate actions, calculations, and data to keep code easy to reason about, test, and change. Use for every coding task — writing, changing, refactoring, reviewing, or designing code — even when the user does not mention functional programming, side effects, testing, or complexity.
---

# Functional Simplicity

Use functional thinking to make code easier to reason about, test, and change.

The core move: separate **actions**, **calculations**, and **data**. Push actions to the edges, make calculations explicit and testable, and represent facts as plain data.

## Scope

Apply these moves to the code you are already changing. Keep the diff proportional to the task: a bug fix must not become a module restructure. Propose larger restructurings instead of performing them. Defer to established repo conventions and native idioms (Rust ownership, React state, framework lifecycles) when they already provide the same guarantees.

## Process

### 1. Classify the touched code

Before editing, classify the relevant code paths:

- **Actions**: depend on when or how often they run, or interact with the outside world. Examples: I/O, database writes, HTTP calls, time, randomness, logging, mutation, global state, caches, queues.
- **Calculations**: deterministic logic. Same explicit inputs produce the same output, with no external effects.
- **Data**: inert values that describe facts, requests, decisions, events, or results.

Completion criterion: every modified behavior has an action/calculation/data classification, and every action boundary is known.

### 2. Extract calculations from actions

Keep actions thin. Move business rules, decisions, transformations, validation, formatting, pricing, routing, eligibility, and policy logic into calculations. Do not hide domain policy inside framework callbacks, and do not move side effects so far from their call sites that control flow becomes obscure.

Prefer this shape:

```text
action:
  read external state
  convert to data
  call calculations
  write external state
```

Avoid this shape:

```text
action:
  read external state
  decide policy
  mutate data
  call service
  branch on hidden state
  write result
```

Completion criterion: the core decision logic can be tested without network, database, clock, randomness, filesystem, process environment, or global mutable state.

### 3. Make inputs and outputs explicit

Remove hidden inputs from calculations. Pass required values as parameters. Return results instead of mutating arguments or relying on ambient state. When changing signatures, keep call sites clear: prefer named data structures over positional argument soup when multi-field inputs or outputs become ambiguous.

Completion criterion: a reader can identify all inputs and outputs of each calculation from its signature and return value.

### 4. Preserve data immutability at boundaries

Default to copy-on-write for changed data. Do not mutate caller-owned structures unless the existing API explicitly promises mutation. Never share mutable objects across async or concurrent boundaries.

At untrusted boundaries, use defensive copying: copy data before passing it to code that may mutate it, copy data received from code that may retain or mutate it later, and normalize external data into internal plain data before calculations use it.

Completion criterion: no new code path can accidentally modify data owned by another layer, caller, cache, request, or concurrent timeline.

### 5. Stratify the design

Keep each function at one level of abstraction:

```text
policy / domain decision
application orchestration
adapter / persistence / transport
primitive utilities
```

A high-level function reads as a small composition of lower-level operations; a low-level function knows nothing about business workflow. Make each layer an abstraction barrier: callers use it without knowing its implementation. Put frequently changing policy above stable utilities. Split mixed-layer functions such as `handleRequestAndCalculateDiscountAndSaveOrder` into orchestration plus calculations.

Completion criterion: each changed function has one clear layer, and callers do not reach around that layer to manipulate internals.

### 6. Replace duplicated control flow with first-class operations

When loops, branching, callbacks, or pipelines repeat the same shape, extract the operation as data or a function: mappers, filters, reducers, validators, predicates, handlers, small combinators.

Only abstract real, existing duplication. Do not turn every function into a tiny abstraction, replace clear loops with unreadable pipelines, or introduce functional jargon the repo does not use. Keep domain names visible. Prefer boring code over clever abstraction.

Completion criterion: repeated control-flow shape is consolidated only where it reduces duplication without hiding the business concept.

### 7. Analyze timelines for async or concurrent code

For async, event-driven, threaded, queued, or distributed behavior, list the timelines. For each: what starts it, what actions it performs, what data it reads and writes, what resources it shares, what ordering it assumes, and what can run concurrently.

Reduce timing bugs by isolating data and making coordination explicit: idempotency, queues, locks, transactions, version checks, retries, or conflict resolution as appropriate. Never rely on ordering that is not enforced in code.

Completion criterion: every shared resource and required ordering is explicit in code, tests, or comments near the coordination point.

### 8. Test by category

Test calculations with fast deterministic unit tests. Test data with schema, parser, serializer, validation, fixture, or property-style tests where useful. Test actions with integration, contract, adapter, or boundary tests; use fakes only when they preserve the action contract. Never require I/O just to verify calculation logic.

Completion criterion: new or changed calculation logic is covered without external effects, and action boundaries have at least one test or existing verified contract.

### 9. Report the simplification

Summarize where complexity moved, what became pure, and which side effects remain intentional. For small changes, one short paragraph is enough. For larger changes, use this format, omitting sections that do not apply:

```text
Actions: ...
Calculations: ...
Data: ...
Side effects moved or isolated: ...
Mutation removed or contained: ...
Timeline/resource risks addressed: ...
Tests: ...
```

Completion criterion: a reviewer can see where complexity moved, what became pure, and which side effects remain intentional.

