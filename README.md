<p align="center"><img src="docs/img/banner.jpg" alt="Illustration: three stone gates under a great ash tree, joined by threads of light" width="100%"></p>

# sistema-produccion

**A multi-model production line: DeepSeek writes, Claude checks sources and reviews, code decides the route, and a person approves.**

Language models write quickly but should not approve their own work. This engine gives each model one job and only the permissions that job needs. Every step leaves a record, and approvals are tied to the exact content by hash.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/img/kpis-dark.svg">
    <img alt="Four figures: 303 tests pass in 7 seconds with no network; 194 of 194 mutants detected; 6 of 6 seeded errors caught, none invented, in one run; 4 model routes, one function each." src="docs/img/kpis-light.svg" width="100%">
  </picture>
</p>

## The pipeline

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/img/pipeline-dark.svg">
    <img alt="Pipeline: a person approves the brief; code builds context packs; DeepSeek writes; code reviews; Claude checks sources with web only; Claude cold-reviews without tools; a person approves; delivery. Findings return to the writer." src="docs/img/pipeline-light.svg" width="100%">
  </picture>
</p>

*A typical line. Each project declares its own stages, gates and correction rounds; LangGraph runs them in order.*

1. **Brief.** A person approves the assignment. The approval stores its sha256.
2. **Context.** Code builds a separate rules pack for each role, so each model receives only its own pack.
3. **Draft.** DeepSeek writes the piece. Missing information is marked instead of filled in, and goes to a person.
4. **Mechanical review.** Pattern rules catch what does not need a model. This step uses no tokens.
5. **Sources.** Claude opens the cited sources on the web and returns confirmed, corrected and unverifiable lists with URLs.
6. **Cold review.** Claude reads the piece without the writer's conversation and returns structured findings: M (mechanical), R (rule) or J (judgement). M and R can go back to the writer within a fixed number of rounds. J goes to a person.
7. **Delivery.** A person signs off. If approved content changes later, that approval and the later stages expire.

## The agents and their permissions

| Role | Runs on | Can do | Cannot do | Output |
|---|---|---|---|---|
| Context builder | Code | Read the files the project declares | Call a model | One pack per role |
| Writer | DeepSeek (`deepseek-v4-pro`) | Read its pack and write text | Use tools or review | Draft |
| Mechanical reviewer | Code | Apply pattern rules | Call a model | JSON report |
| Source checker | Claude Sonnet | `WebSearch` and `WebFetch` | Use a shell or write files | Validated JSON with URLs |
| Cold reviewer | Claude Sonnet | Read its pack and the piece | Use tools | Validated JSON findings |
| Router | Code (LangGraph) | Follow the declared stages | Let a model choose the route | Records and state |
| Approver | Person | Approve or return | Skip the record | Record tied to a hash |

Model names are the ones used in the recorded runs; they are set by each project. Four routes exist behind one interface: `deepseek`, `claude`, `opencode` (free models) and `ollama` (local). A step can list fallback routes, tried in order until one returns a valid result. Code: `motor/nodos.py`, `motor/modelos.py`.

## Design choices

| Choice | How it works | Code and tests |
|---|---|---|
| Code decides the route | A line declares stages, dependencies, gates and maximum rounds. Invalid lines are rejected | `motor/state.py`, `pruebas/test_state.py` |
| The writer is not the reviewer | Writing is limited to DeepSeek; the reviewer runs through Claude | `motor/nodos.py`, `pruebas/test_borrador.py` |
| Least privilege | Claude and opencode run in temporary folders. Claude can be given only two web tools | `motor/modelos.py`, `pruebas/test_modelos.py` |
| Outgoing data is checked | A filter stops a call to a non-local model when it finds private terms or known patterns | `motor/saneo.py`, `pruebas/test_saneo.py` |
| Files are the source of truth | Hash-sealed manifests rebuild the state; the LangGraph checkpoint can be deleted | `motor/state.py`, `motor/runtime.py` |
| Controls are tested by breaking them | 194 deliberate faults were injected and the tests detected all of them | `pruebas/mutantes/mutar.py` |
| Cost is measured | Tokens, cost, failures and rounds by stage, role and model | `motor/medir.py` |

## Results from real runs

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/img/cost-dark.svg">
    <img alt="Bar chart for one real run with two versions of the piece: reviewers (Claude Sonnet) 0.73 US dollars, API-equivalent; writer (DeepSeek) 0.15 US dollars, billed." src="docs/img/cost-light.svg" width="100%">
  </picture>
</p>

In one end-to-end run with two versions of a piece, the writer cost 0.15 US dollars billed and the Claude reviews 0.73 US dollars API-equivalent.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/img/loop-dark.svg">
    <img alt="Stacked columns of findings per round: round 1 had 8 returned to the writer and 1 needing a person; round 2 had 2 and 1." src="docs/img/loop-light.svg" width="100%">
  </picture>
</p>

In that run, findings to correct went from 8 in round 1 to 2 in round 2, with 1 for a person in each. In a separate test on one piece, the cold reviewer caught 6 of 6 planted errors and invented none. Run notes are not included in this sample.

Real runs also shaped the code: the DeepSeek route now streams and rejects a response that ends without `[DONE]`, and the engine, not the model, decides whether a finding is repeated.

## What you can plug in

| Add | By writing | Where |
|---|---|---|
| A model | One function, `Pedido -> Respuesta` | `motor/modelos.py` |
| A step | One function, `Contexto -> Resultado` | `motor/runtime.py` |
| A domain | An `instancia.toml` and its rule files | `plantillas/instancia/` |
| A gate or correction loop | A dictionary entry | `motor/state.py` |

## Possible uses and next steps

None of these is built yet:

- **Code review:** agents would propose diffs, and tests and mutants would run as a stage.
- **Documentation and release notes:** a new domain would need only its own rules.
- **Image production:** ComfyUI, used locally for the banner above, could become a step with its own review gate.
- **Parallel reviewers:** different model families could review the same piece, with reports merged by rule.
- **Evaluation bench:** planted errors would measure a reviewer before and after a prompt change.
- **Spending cap:** the cost report could become a gate.
- **Business tools:** CRM or database steps would sit behind the same filter, with declared permissions.

## Run it

```bash
/usr/bin/python3.12 -m venv .venv
.venv/bin/pip install --require-hashes -r requirements.lock
.venv/bin/pip install pytest
.venv/bin/pytest
.venv/bin/python pruebas/mutantes/mutar.py
python3 docs/figuras/generar.py
python3 docs/figuras/flujo.py
```

The tests use no network and spend nothing. The last two commands need matplotlib.

## Scope

This is a working sample that runs locally, one step at a time, with one approver. Code and templates are in Spanish. Cost and review figures come from single runs, and a clean review does not prove a piece has no errors. Current gaps: returning a piece at the review gate repeats the review instead of calling the writer; changed rules raise a warning but do not rerun a stage; and gate notes reach the model as plain text.

Drafted with the engine (DeepSeek and Claude), edited with Gemini and Claude Code.
