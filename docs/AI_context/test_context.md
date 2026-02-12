# Test Context Execution Plan

This ExecPlan obeys `docs/AI_context/PLANS.md` and defines the general workflow Codex should follow when preparing DDD-informed reviews and test plans for any `/src` classes. Treat it as a living document: update it whenever the review checklist, observations, or guardrails change before modifying production code.

## Purpose / Big Picture

Provide a consistent prompt grounding so that every time Codex is asked to review one or more `/src` classes, it first evaluates the requested classes against the DDD guardrails (aggregate boundaries, invariants, context map, dependency direction, entity/value-object roles), records those findings in this plan, and then produces an execution plan that details the intended tests, any required code comments, and the review outcomes. As part of the goal, recommend adding standardized code comments that explain a class's responsibility or key invariants where clarity would benefit future reviews, specifying the exact location (class docstring, method docstring, etc.) and the rationale for the comment. In addition to the DDD checklist, ensure the review records how each class aligns with these "Good Python Practices": keep code readable with clear structure and comments, enforce typing discipline (explicit annotations and dataclasses), document behavior via docstrings, manage resources safely through context managers and cleanup, and use consistent naming for functions, classes, and variables. Mention deviations in the `Surprises & Discoveries` section.

## How to use this document

1. Name the `/src` classes you want reviewed when you prompt Codex so the plan applies directly.
2. Apply the DDD checklist and Good Python Practices above to those classes, log the outcomes here, and note any recommended standardized comments (including location plus rationale).
3. Return a fresh execution plan that includes the review findings, suggested comments, and a test strategy before editing code.

## Progress

- [x] (2026-01-24 00:00Z) Captured the need for pre-test DDD reviews plus ExecPlan visibility.
- [ ] (2026-01-24 00:05Z) Populate `docs/ai_context/test_context.md` with the ExecPlan that maps review findings to tests.

## Surprises & Discoveries

- Observation: Review sessions often surface repeated patterns, such as DTO constructors validating configuration constants, services orchestrating aggregates without back-propagating dependencies, and invariants relying on shared registries. Treat these patterns as hypotheses and validate them each time.
  Evidence: Observations from previous reviews where mis-specified context-map constants or mutable DTOs demanded explicit unit coverage.

## Review Findings

- Capture the key invariants, aggregate boundaries, Good Python Practice observations, and recommended comment opportunities discovered in the current review.
  Example: "Invalid context-map inputs are rejected in `FooDTO.is_valid()`; consider documenting this in the class docstring as part of the Bronze ingest contract."

## Decision Log

- Decision: Treat the objects under review as either immutable value objects (when their identity is irrelevant) or aggregates/entities (when their state changes across the workflow) and write tests against whichever role applies.
  Rationale: This preserves the DDD semantics of clear boundaries and intentional mutations.
  Date/Author: 2026-01-24 / Codex.

## Outcomes & Retrospective

Once this plan is applied, each Codex run will: 
(1) review the specified classes against the DDD checklist plus the Good Python Practices described above, 
(2) record those review findings in this plan, and 
(3) output a dedicated execution plan that describes the unit/integration tests, required code comments (including location and rationale), and observations that verify the documented guardrails. 
Save that execution plan as a new file under `/docs/prompts`.
Updating the living sections after each review keeps the context current for future contributors.

## Context and Orientation

The prompt must specify which `/src` classes are in scope. This plan does not assume any fixed files; instead, it defines how to orient the reviewer once the classes are known. Codex should describe the domain purpose of the classes provided, note their dependencies, and highlight what invariants or aggregates they touch.

DDD review checklist (run before coding and document here):

1. **Aggregate boundaries** - Identify what constitutes an aggregate root in the supplied class set and confirm that it owns the transactional invariants while collaborators remain read-only.
2. **Invariants** - Enumerate the runtime checks each class performs (e.g., configuration validation, identifier limits, timing requirements) and confirm they are explicit and testable.
3. **Context map consistency** - Verify that configurable domain/source/dataset/cadence values (or their equivalents in the supplied classes) are sourced from the shared configuration/constants and not redefined locally.
4. **Dependency direction** - Ensure the reviewed classes depend only on lower-level contracts (DTOs, configuration, helpers) and do not introduce circular references back to higher-level services.
5. **Entity vs. value-object identification** - Distinguish value objects (immutable data carriers) from entities (stateful aggregates) so the tests focus on the appropriate behavior.

## Plan of Work

1. Review the supplied `/src` classes and summarize how each of the checklist items applies. For each class, identify the aggregate it participates in, the invariants it enforces, the configuration constants it reads, the directions of its dependencies, how it measures up against the Good Python Practices, and whether the class behaves as an entity or value object. Suggest where standardized comments could clarify responsibilities or invariants (including the suggested location and rationale), and record these findings in this plan (e.g., under `Surprises & Discoveries` or `Review Findings`) before changing code.
2. Translate each observation into one or more concrete test targets. For context-map issues, describe tests that supply invalid constants and assert rejection. For invariants related to identifiers or timing, define tests that cover the boundary conditions. For aggregate boundaries, specify the key service/method calls that should be mocked or stubbed in the tests to keep state within the aggregate.
3. Write the ExecPlan steps that explain how Codex or another agent should implement the tests, referencing the recorded observations. Always remind readers to revisit this document and update the living sections if new findings appear mid-work.

## Concrete Steps

1. From `c:\sb\SBFoundation`, inspect the `/src` files named in the prompt to verify the DDD checklist and Good Python Practices still apply; update `Surprises & Discoveries` and `Review Findings` with any new observations.
2. Before changing code, refresh the relevant sections (Progress, Surprises & Discoveries, Review Findings, Decision Log) in whichever ExecPlan you create for the prompt so the living record reflects the current review.
3. After documenting the review findings, describe the test cases needed to cover each invariant or guard in the classes under review, and mention where added comments would reinforce the documented behavior.

## Validation and Acceptance

The document is valid when it instructs future Codex runs to mention the supplied classes, evaluate them against the DDD checklist and Good Python Practices, log the findings, and then produce an execution plan that explains the intended tests, necessary comments (location + rationale), and how the guardrails were verified. Acceptance looks like a prompt that references this plan, includes the target classes, and requests an execution plan anchored to the checklist.

## Idempotence and Recovery

Overwriting this document with an updated plan is safe. To recover a previous version, restore it from version control.

## Artifacts and Notes

- When the review uncovers a new invariant or context-map dependency, add it to `Surprises & Discoveries` and tie a test idea to it immediately.
- Keep track of whether the class under review is acting as a value object or entity; mixing the two without clarity causes brittle tests.

## Interfaces and Dependencies

- List the relevant entry points, helper methods, registries, or configuration values the classes in each prompt rely on.
- Call out shared constants or placeholder helpers to ensure the test plan references the right contracts.

## Example prompt

Use this plan before modifying `/src`. For example:

> "Review `ModuleA` and `ModuleB` using the aggregate boundary, invariants, context map, dependency direction, and entity/value-object checklist above. Record the findings in the ExecPlan's `Surprises & Discoveries` section, then outline unit tests that exercise each observation before editing the code and save the resulting ExecPlan as a new file under `/docs/prompts`."
