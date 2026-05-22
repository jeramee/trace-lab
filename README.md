# TraceLab

**Adapter-aware evidence orchestration for instrumented research.**

`TraceLab` (`trace-lab`) is a proposed NeuML-aligned project that extends `txtai`, PaperAI, and paperetl from document intelligence into physical and instrumented experimental workflows.

It connects experiment requests, run plans, scoped approvals, LabVIEW-like and open-source control systems, simulated or adapter-backed actions, telemetry, datasets, notebooks, reports, validation records, evidence packets, and human review into traceable research workflows.

Status: proposed product/research concept. Not an existing official NeuML product unless adopted by NeuML.

---

## v0.1 simulated scaffold commands

TraceLab v0.1 is simulation-only and has no runtime dependencies beyond Python. The current scaffold can create a demo evidence chain, validate operational record presence, and build a future NeuML handoff manifest without calling NeuML, txtai, PaperAI, paperetl, or hardware APIs.

```bash
python -m trace_lab.cli run-demo --out .trace_lab_demo
python -m trace_lab.cli validate --run-dir .trace_lab_demo --write-result
python -m trace_lab.cli state-summary --run-dir .trace_lab_demo --write
python -m trace_lab.cli review-summary --run-dir .trace_lab_demo
python -m trace_lab.cli adapter-summary --run-dir .trace_lab_demo
python -m trace_lab.cli adapter-summary --run-dir .trace_lab_demo --write
python -m trace_lab.cli environment-summary --run-dir .trace_lab_demo --write
python -m trace_lab.cli policy-summary --run-dir .trace_lab_demo --write
python -m trace_lab.cli telemetry-profile --run-dir .trace_lab_demo --write
python -m trace_lab.cli ingestion-preview --run-dir .trace_lab_demo --write
python -m trace_lab.cli provenance-summary --run-dir .trace_lab_demo --write
python -m trace_lab.cli closeout-summary --run-dir .trace_lab_demo --write
python -m trace_lab.cli claim-summary --run-dir .trace_lab_demo --write
python -m trace_lab.cli review-packet --run-dir .trace_lab_demo --write
python -m trace_lab.cli report --run-dir .trace_lab_demo --write
python -m trace_lab.cli verify-report --run-dir .trace_lab_demo --write-result
python -m trace_lab.cli export-bundle --run-dir .trace_lab_demo --out .trace_lab_demo_export.zip
python -m trace_lab.cli verify-bundle --bundle .trace_lab_demo_export.zip --write-result
python -m trace_lab.cli build-neuml-handoff --run-dir .trace_lab_demo
python -m trace_lab.cli validate --run-dir .trace_lab_demo
python -m unittest discover -s tests -v
```

Authority boundary: evidence is not proof; operational validation is not scientific validity; handoff is not promotion; simulation is not physical execution.

`run-demo` refuses to write into a non-empty output directory. Remove the old demo folder or choose a new run directory before creating another simulated run. This prevents silent overwrite of run evidence.

## v0.1 human-review gate

TraceLab now writes `review_record.json` as a human-required review checkpoint. The record intentionally remains in `pending_human_trace_review` status. It does not complete human review, validate scientific truth, allow automatic promotion, or authorize hardware execution.

Use the operator-facing review summary command to inspect that boundary:

```bash
python -m trace_lab.cli review-summary --run-dir .trace_lab_demo
python -m trace_lab.cli review-summary --run-dir .trace_lab_demo --write
```

`review_summary.json` is a view artifact only. It is not claim promotion.



## v0.1 adapter boundary summary

TraceLab now validates the simulated-adapter boundary as its own operational seam. The adapter capability manifest, dry-run record, and simulated action record must agree on the adapter identity, action type, parameters, and simulation-only execution mode. Forbidden hardware-control fields such as serial ports, device paths, LabVIEW VI paths, OPC UA endpoints, Modbus addresses, and driver modules are rejected in v0.1.

Use the operator-facing adapter summary command to inspect that boundary:

```bash
python -m trace_lab.cli adapter-summary --run-dir .trace_lab_demo
python -m trace_lab.cli adapter-summary --run-dir .trace_lab_demo --write
```

`adapter_boundary_summary.json` is a view artifact only. It does not call hardware, approve execution, validate scientific truth, or promote claims.


## v0.1 local export bundle

TraceLab can package a validated simulated run into a local ZIP bundle:

```bash
python -m trace_lab.cli export-bundle --run-dir .trace_lab_demo --out .trace_lab_demo_export.zip
python -m trace_lab.cli export-bundle --run-dir .trace_lab_demo --out .trace_lab_demo_export.zip --dry-run
```

The export command first checks operational validation. It refuses failed runs and refuses silent overwrite unless `--force` is explicitly provided. The ZIP contains `trace_lab_export_manifest.json`, the hashed run records, telemetry artifact, and optional operator-facing summaries that already exist in the run folder.

The export bundle is packaging evidence only. It does not call NeuML, txtai, PaperAI, paperetl, hardware APIs, networks, or package installers. It does not validate scientific truth or promote claims.


## Product description

TraceLab is an adapter-aware evidence orchestrator for instrumented research.

It is not trying to reinvent LabVIEW, MATLAB/Simulink, Bluesky, Flojoy, PyLabRobot, EPICS, TANGO, PyVISA, PySerial, QCoDeS, PyMeasure, vendor SDKs, or existing laboratory control systems. Those tools already solve important parts of instrument control, telemetry capture, simulation, automation, or real-time execution.

TraceLab's role is different:

> TraceLab records the evidence boundary around instrumented research.

It preserves the path from experiment intent to run plan, approval, adapter capability, dry-run result, action record, telemetry manifest, validation record, evidence packet, and human review.

---

## Core principle

Every lab action should be traceable.  
Every validation should be recorded.  
Every durable claim should remain human-promoted.

---

## Why this belongs in the NeuML stack

NeuML already has a strong AI infrastructure stack:

| NeuML project | Current role | TraceLab relationship |
|---|---|---|
| `txtai` | Semantic search, embeddings, RAG, workflows, agents, APIs, and multimodal indexing | Search, retrieve, summarize, compare, and reason over lab evidence packets |
| `paperetl` | ETL processes for medical and scientific papers | Inspires ingestion of protocols, instrument logs, telemetry tables, notebook outputs, and run artifacts |
| `paperai` | AI-assisted workflows for medical and scientific papers | Can consume lab evidence packets alongside literature for scientific reporting |
| `rag` | Retrieval Augmented Generation with `txtai` | Can answer questions over experiment records and evidence packets |
| `txtchat` | Local chat assistants with AI superpowers | Can become a local operator/reviewer assistant over lab evidence |
| `annotateai` | Automatically annotate papers using LLMs | Can inspire protocol, run-note, telemetry, and evidence annotation |
| RunLab | User-facing Jupyter/JupyterLab reproducible research workbench | Can consume TraceLab evidence packets and turn them into notebook-backed reports |
| TraceLab | Proposed trace-governed experimental evidence layer | Captures lab-run evidence before it becomes a paper, report, dataset, or RAG source |

TraceLab does not replace `txtai`, PaperAI, paperetl, RunLab, Jupyter, or instrument-control systems. It gives them a new class of source material: structured, reviewable experimental evidence.

---

## Problem

Reproducible research should not stop at notebooks, papers, RAG answers, and generated reports.

Many scientific claims begin in instrumented workflows:

- a run plan is approved;
- a device action is attempted;
- telemetry is captured or missing;
- an operator intervenes;
- an instrument fails;
- a dataset is generated;
- a notebook or report is produced;
- a reviewer accepts, rejects, or requests follow-up.

If those events are scattered across device logs, file shares, notes, emails, local GUIs, and memory, then the final paper or RAG answer is only the computational surface of the work.

TraceLab makes that experimental chain inspectable.

---

## What TraceLab is

TraceLab is a proposed trace-governed evidence workbench for reproducible experimental science.

It is:

- an evidence layer for physical and instrumented experiments;
- an operator console for safe work movement;
- a record family for experiment requests, run plans, approvals, adapter actions, telemetry, validation, and review;
- an adapter-aware orchestration layer above existing lab-control systems;
- a bridge from lab evidence into `txtai`-powered search, RAG, workflows, RunLab notebooks, and PaperAI-style reporting.

---

## What TraceLab is not

TraceLab is not:

- an open-source LabVIEW clone;
- a replacement for MATLAB/Simulink or Simulink Coder;
- a replacement for Bluesky, Flojoy, PyLabRobot, EPICS, TANGO, PyVISA, PySerial, QCoDeS, PyMeasure, or vendor SDKs;
- an autonomous lab agent;
- an ORCA clone;
- a generic industrial IoT dashboard;
- a universal hardware-control framework;
- a safety certification system;
- a scientific truth engine;
- a way for agents to silently operate instruments.

TraceLab may interface with control systems. It should not become the authority that approves physical execution, retries hardware, bypasses interlocks, or promotes scientific claims.

---

## Instrumentation interface strategy

TraceLab should interface with instrumentation by adapters, manifests, dry-run records, and telemetry records.

It should start with simulation and telemetry-only lanes before any real actuation.

```text
Instrumentation / control layer
  LabVIEW
  MATLAB / Simulink / Simulink Coder
  Bluesky + Ophyd
  Flojoy
  PyLabRobot
  EPICS
  TANGO
  PyVISA / PySerial / PyMeasure / QCoDeS
  Vendor SDKs
  File / CSV / JSON / serial / socket / REST / MQTT telemetry

TraceLab
  experiment request
  run plan
  approval record
  adapter capability manifest
  dry-run result
  adapter action record
  telemetry manifest
  validation record
  evidence packet
  human review record

txtai / RunLab / PaperAI
  search over run evidence
  RAG over experiment packets
  compare runs
  summarize failures
  draft reports
  connect literature evidence with lab evidence
```

TraceLab should not pretend that all instrumentation ecosystems are the same. A file telemetry adapter, a serial data feed, a Bluesky plan, a PyVISA command, a LabVIEW export, and an EPICS process variable all have different risk and authority profiles.

The adapter model should capture:

- what the adapter can observe;
- what the adapter can propose;
- what the adapter can dry-run;
- what the adapter can execute, if anything;
- what approval is required;
- what telemetry is expected;
- what failure states must be recorded;
- what the system is not allowed to do.

---

## Product thesis

NeuML's current stack is strong at semantic search, RAG, LLM workflows, scientific literature processing, and AI-assisted reporting.

The missing next layer is experimental evidence.

TraceLab brings lab-run evidence into the NeuML stack by preserving:

- experiment intent;
- proposed run plans;
- scoped human approvals;
- policy and capability checks;
- simulated or adapter-backed actions;
- telemetry manifests;
- validation records;
- evidence packets;
- human review and promotion decisions.

---

## Architecture

```text
TraceLab
|
|-- Operator Console
|   |-- work queue
|   |-- approvals
|   |-- blockers
|   |-- evidence timeline
|   |-- review panel
|
|-- Experiment Run Model
|   |-- experiment request
|   |-- run plan
|   |-- ordered steps
|   |-- adapter action proposals
|   |-- telemetry references
|   |-- review state
|
|-- Policy / Capability Boundary
|   |-- actor permissions
|   |-- adapter capability manifests
|   |-- command schemas
|   |-- dry-run requirements
|   |-- retry restrictions
|   |-- risk tiers
|
|-- Adapter Layer
|   |-- simulated adapter first
|   |-- PC-hub/file/serial telemetry later
|   |-- LabVIEW / MATLAB export adapters later
|   |-- Bluesky / Flojoy / PyVISA / PySerial later
|   |-- PyLabRobot later
|   |-- EPICS / TANGO later
|
|-- Evidence Packet Layer
|   |-- manifests
|   |-- hashes
|   |-- artifacts
|   |-- known gaps
|   |-- not-proven claims
|
|-- txtai + RunLab + PaperAI Integration Layer
|   |-- semantic search over run evidence
|   |-- RAG over experiment packets
|   |-- notebook-backed reproducible reports
|   |-- report drafting from lab evidence
|   |-- run comparison and summarization
|
|-- Review / Promotion Layer
    |-- validation checks
    |-- human review
    |-- accepted/rejected/follow-up claims
```

---

## Record family

The minimum record family is the project center:

| Record | Purpose | Authority boundary |
|---|---|---|
| `experiment_request.json` | Captures why the run exists and what question it addresses | Intent only; not execution authorization |
| `run_plan.json` | Converts intent into proposed steps, expected outputs, and checks | Proposal only until approved |
| `approval_record.json` | Records who approved what and under what scope | Scoped and non-transferable |
| `adapter_capability_manifest.json` | Declares what an adapter can observe, simulate, dry-run, or execute | Capability statement, not permission |
| `dry_run_record.json` | Records proposed execution without physical actuation | Readiness evidence, not approval |
| `adapter_action_record.json` | Records proposed, simulated, executed, blocked, or failed actions | Execution evidence, not scientific truth |
| `telemetry_manifest.json` | Links logs, streams, files, device states, and missing telemetry to the run | Completeness evidence, not interpretation |
| `validation_record.json` | Records mechanical checks, schema checks, bounds checks, or policy checks | Operational validation, not scientific proof |
| `lab_run_record.json` | Ties request, plan, approvals, actions, telemetry, artifacts, checks, and review | Run spine, not final claim |
| `evidence_packet_manifest.json` | Bundles records, artifacts, hashes, gaps, replay references, and limitations | Inspectable support, not authority |
| `review_record.json` | Captures accepted, rejected, and unresolved claims | Human promotion boundary |

---

## Agent role

Agents may help by:

- finding missing metadata;
- drafting run plans;
- generating checklists;
- comparing runs;
- summarizing failed runs;
- drafting reports from recorded artifacts;
- recommending follow-up questions;
- preparing review packets for humans;
- searching prior lab evidence with `txtai`.

Agents must not:

- approve execution;
- change device parameters without approval;
- retry failed physical actions automatically;
- bypass interlocks;
- decide scientific validity;
- promote durable claims;
- hide missing telemetry;
- overwrite run records;
- broaden hardware permissions;
- turn dry-run capability into real actuation.

---

## How txtai fits

`txtai` is the natural retrieval and workflow substrate for this project.

Possible future uses:

- index evidence packet manifests;
- search operator notes, run summaries, telemetry summaries, and validation records;
- build RAG over lab-run evidence;
- compare one run to another;
- summarize failed runs;
- draft reports from evidence packets;
- expose evidence search through APIs or MCP-compatible tools.

The important boundary: `txtai` can retrieve, summarize, and orchestrate evidence workflows, but it should not become the authority that approves physical execution or promotes scientific claims.

---

## How RunLab fits

RunLab is the user-facing Jupyter Notebook/JupyterLab reproducible research workbench.

TraceLab can feed RunLab with instrumented evidence packets. RunLab can then run notebook-backed analysis and reporting workflows over that recorded evidence.

```text
TraceLab
  -> structured lab-run evidence packets

RunLab
  -> notebook-backed analysis, reports, replay manifests, and evidence inspection

txtai / PaperAI
  -> search, compare, summarize, cite, and report over literature + lab evidence
```

---

## How PaperAI and paperetl fit

`paperetl` and PaperAI already move NeuML toward scientific and medical literature intelligence.

TraceLab extends that path:

```text
paperetl
  -> structure the literature

PaperAI
  -> search, chat, and report over scientific papers

txtai
  -> retrieve, orchestrate, and expose workflows

RunLab
  -> execute notebook-backed reproducible research runs

TraceLab
  -> capture experimental evidence before it becomes a paper
```

A future PaperAI-style report could cite both:

1. published literature; and
2. local lab evidence packets produced by TraceLab.

---

## Roadmap

### Phase 0: Design only

- Research paper.
- SRS seed.
- README.
- Record contracts.
- Adapter strategy.
- No code.
- No hardware.

### v0.1: Simulated lab-run evidence lane

Goal: prove the evidence path without hardware.

In scope:

- fake experiment request;
- fake run plan;
- scoped approval record;
- fake adapter capability manifest;
- simulated dry-run record;
- simulated action record;
- fake telemetry manifest;
- validation record;
- evidence packet manifest;
- human review record.

Out of scope:

- real devices;
- hardware APIs;
- GUI automation;
- agent-owned validation;
- agent-owned promotion.

### v0.2: Adapter contract and dry-run lane

Goal: define capability manifests, command schemas, dry-run behavior, rejection records, and approval boundaries.

Out of scope:

- physical execution;
- autonomous retry;
- unapproved actuation.

### v0.3: Telemetry-only PC-hub lane

Goal: ingest real but non-actuating telemetry from files, serial logs, sockets, REST exports, CSV/JSON records, or dummy instruments.

Out of scope:

- controlling instruments;
- changing device state;
- silent background execution.

### v0.4: LabVIEW-like and scientific Python adapter studies

Goal: design adapter contracts for existing ecosystems without cloning them.

Candidate interface families:

1. LabVIEW export/log/file interface.
2. MATLAB/Simulink export/log interface.
3. Bluesky/Ophyd plan and run metadata.
4. Flojoy workflow outputs.
5. PyVISA/PySerial/PyMeasure/QCoDeS bench-instrument records.
6. PyLabRobot dry-run and liquid-handling metadata.
7. EPICS/TANGO telemetry references.

### v1.0: One bounded adapter-backed workflow

Goal: integrate one carefully chosen adapter family after simulation, dry-run, and telemetry-only evidence are stable.

Likely adapter order:

1. Simulated adapter.
2. File/CSV/JSON/serial telemetry adapter.
3. Bluesky or Flojoy.
4. PyVISA/PySerial/PyMeasure/QCoDeS bench-instrument record adapter.
5. PyLabRobot later.
6. EPICS/TANGO later.

---

## Standards alignment

TraceLab should map to existing evidence and provenance patterns:

- W3C PROV: activities, entities, and agents;
- RO-Crate: evidence packet packaging;
- FAIR/FAIR4RS: reusable software and artifact metadata;
- Frictionless Data Package: simple tabular telemetry and dataset descriptions;
- DataCite / CodeMeta / CITATION.cff: future citation metadata;
- SPDX / SBOM: optional future dependency and license metadata.

---

## First contributor target

Do not start with hardware.

The first useful contributor target is a design-only SRS seed that freezes:

- simulated v0.1 scope;
- record family;
- state model;
- authority flags;
- adapter capability manifests;
- instrumentation interface strategy;
- adapter ladder;
- `txtai`, RunLab, and PaperAI integration points;
- ship/do-not-ship gates.

---

## GitHub description

Adapter-aware evidence orchestration for instrumented research, connecting experiment plans, approvals, LabVIEW-like and open-source control systems, telemetry, validation records, evidence packets, and human review into traceable research workflows.

---

## References

- NeuML: https://neuml.com/
- NeuML GitHub: https://github.com/neuml
- txtai: https://github.com/neuml/txtai
- txtai docs: https://neuml.github.io/txtai/
- txtai tutorial series: https://neuml.hashnode.dev/series/txtai-tutorial
- paperai: https://github.com/neuml/paperai
- paperetl: https://github.com/neuml/paperetl
- rag: https://github.com/neuml/rag
- txtchat: https://github.com/neuml/txtchat
- annotateai: https://github.com/neuml/annotateai
- JupyterLab: https://jupyterlab.readthedocs.io/
- Papermill: https://papermill.readthedocs.io/
- LabVIEW: https://www.ni.com/en/shop/labview.html
- MathWorks LabVIEW connection page: https://www.mathworks.com/products/connections/product_detail/labview.html
- Simulink Coder: https://www.mathworks.com/products/simulink-coder.html
- Bluesky Project: https://blueskyproject.io/
- Ophyd: https://blueskyproject.io/ophyd/
- Flojoy: https://www.flojoy.ai/
- PyLabRobot: https://docs.pylabrobot.org/
- PyVISA: https://pyvisa.readthedocs.io/
- PySerial: https://pyserial.readthedocs.io/
- PyMeasure: https://pymeasure.readthedocs.io/
- QCoDeS: https://microsoft.github.io/Qcodes/
- EPICS: https://epics-controls.org/
- TANGO Controls: https://www.tango-controls.org/
- W3C PROV: https://www.w3.org/TR/prov-dm/
- RO-Crate: https://www.researchobject.org/ro-crate/specification/1.2/index.html
- Frictionless Data Package: https://specs.frictionlessdata.io/data-package/

---

## Status

Planning/design draft.

No code. No hardware. No repo mutation. No scientific truth claims.


## Current v0.1 validation boundaries

TraceLab validation is operational only. It checks required records, JSON readability, telemetry file presence/hash integrity, evidence artifact presence/hash integrity, record-link integrity, simulation-only approval scope, and authority flags that must remain false. These checks do not prove scientific truth, physical safety, hardware readiness, or claim promotion.


## Run-state machine

TraceLab v0.1 writes `run_state_chain.json` during `run-demo`. The chain is a simulation-only operational lifecycle:

```text
requested -> planned -> approved_for_simulation_only -> dry_run_checked -> simulated_action_recorded -> telemetry_recorded -> evidence_packet_built -> operationally_validated -> review_required -> handoff_prepared
```

Inspect it from the CLI:

```bash
python -m trace_lab.cli state-summary --run-dir .trace_lab_demo
python -m trace_lab.cli state-summary --run-dir .trace_lab_demo --write
```

The state chain does not approve hardware, validate scientific truth, or promote claims.

## NeuML handoff preflight

`build-neuml-handoff` is guarded by a mechanical preflight. TraceLab refuses to prepare `neuml_handoff_manifest.json` when required run records, evidence packet references, run-state chain, or telemetry candidates are missing.

This guard prevents a future-ingestion artifact from making an incomplete run look handoff-ready. It is still only an operational completeness check:

- it does not call NeuML, txtai, PaperAI, or paperetl;
- it does not validate scientific truth;
- it does not approve execution;
- it does not promote claims;
- it does not imply hardware readiness.

The validator reports malformed handoff manifests under `handoff_errors`.

## v8 validation-result persistence checkpoint

TraceLab now supports an explicit `validate --write-result` CLI path that writes `validation_result.json` as a bounded operational evidence artifact. The writer refuses silent overwrite unless `--force-result` is used. The persisted result preserves the v0.1 authority boundary: operational validation is not scientific validity, does not execute hardware, does not retry, and does not promote claims.

## Run manifest hash index

TraceLab writes `run_manifest.json` during the demo run. This manifest hashes the core JSON records and telemetry artifact for mechanical drift detection. The validator reports run-manifest problems under `manifest_errors`. This remains operational evidence only: it does not validate scientific truth, approve hardware execution, or promote durable claims.



## Runtime environment manifest

The demo writes `runtime_environment_manifest.json` to capture local Python/runtime context for reproducibility. This is operational evidence only and does not validate scientific truth.

```powershell
python -m trace_lab.cli environment-summary --run-dir .trace_lab_demo
python -m trace_lab.cli environment-summary --run-dir .trace_lab_demo --write
```

The summary preserves the v0.1 boundary: no package installation, no network calls, no hardware access, no execution approval, and no promotion.


## Local export bundle verification

TraceLab can verify a previously exported local evidence bundle without unpacking
or executing it:

```bash
python -m trace_lab.cli verify-bundle --bundle .trace_lab_demo_export.zip
```

Bundle verification checks the embedded `trace_lab_export_manifest.json`, declared
file hashes, declared file sizes, unsafe paths, unexpected files, and authority
flags. It is still packaging-integrity validation only. It does not validate
scientific truth, execute hardware, call networks, install packages, or promote
claims.


### Verify an export bundle and persist the verification result

```powershell
python -m trace_lab.cli verify-bundle --bundle .trace_lab_demo_export.zip --write-result
```

This writes a local sidecar result at `.trace_lab_demo_export.zip.validation.json` unless `--result-out` is provided. The result is packaging evidence only, not scientific validation or claim promotion.

- `report` prints or writes a local Markdown evidence report (`trace_lab_report.md`) without validating scientific truth or promoting claims.

## v17 report verification

TraceLab can now verify the generated local Markdown report with `verify-report`.
This check is a readability-boundary validation only: it confirms required boundary
phrasing and false authority flags remain present. It does not validate scientific
truth, execute hardware, approve actions, call networks, install packages, or
promote claims. Use `--write-result` to persist `trace_lab_report.md.validation.json`.


### Execution policy summary

TraceLab v0.1 records a simulation-only execution policy in `execution_policy_manifest.json`. Use:

```powershell
python -m trace_lab.cli policy-summary --run-dir .trace_lab_demo --write
```

The policy makes the no-hidden-retry boundary explicit and does not approve, execute hardware, validate scientific truth, or promote claims.


## v19 telemetry profile checkpoint

TraceLab now writes `telemetry_profile_manifest.json` during the simulated demo run and supports `telemetry-profile` for an operator-facing data-shape summary. The profile records CSV shape, columns, row count, file hash agreement, and numeric-column ranges as mechanical evidence only. It does not infer sensor correctness, validate scientific truth, approve hardware readiness, or promote claims.


## v20 ingestion preview / local index candidate manifest

- Added `src/trace_lab/ingestion_preview.py`.
- Demo runs now write `ingestion_preview_manifest.json`.
- CLI includes `ingestion-preview`, `ingestion-preview --write`, and `ingestion-preview --write-manifest`.
- Validation reports `ingestion_errors` for authority drift, unsafe candidate paths, candidate count drift, and malformed candidate sections.
- Run manifest, NeuML handoff rebuilds, Markdown report, and export bundle paths now include ingestion-preview evidence where appropriate.
- This is a local index preview only; it does not call NeuML/txtai/PaperAI, run models, perform ingestion, validate scientific truth, or promote claims.


## v21 provenance manifest

Adds `provenance_manifest.json`, `provenance-summary`, and validation for local evidence-origin metadata. This remains simulation-only and does not validate scientific truth, execute hardware, approve actions, or promote claims.


## Run closeout

TraceLab can write a local closeout stop-line for a simulated run:

```bash
python -m trace_lab.cli closeout-summary --run-dir .trace_lab_demo --write
```

This creates `run_closeout_summary.json`. The generated demo also records `run_closeout_manifest.json`.

Closeout is not approval, scientific validation, hardware readiness, or claim promotion. It is an operator-facing indication that the local simulated trace has the expected evidence shape for review/export.

### Claim ledger

TraceLab can write a local claim-boundary ledger:

```bash
python -m trace_lab.cli claim-summary --run-dir .trace_lab_demo --write
```

This creates `claim_ledger_summary.json` and relies on `claim_ledger_manifest.json`. It distinguishes operational evidence from not-proven claims. It does not validate scientific truth, complete human review, approve physical execution, or promote claims.


## Operator review packet

TraceLab can write a local human-review packet manifest and summary:

```bash
python -m trace_lab.cli review-packet --run-dir .trace_lab_demo
python -m trace_lab.cli review-packet --run-dir .trace_lab_demo --write
```

This creates `operator_review_packet_summary.json` and relies on `operator_review_packet_manifest.json`. The packet is a navigation/checklist artifact for a human reviewer. It does not complete human review, validate scientific truth, approve physical execution, or promote claims.


## v25 Replay plan manifest

Adds a local replay checklist manifest and summary (`replay_plan_manifest.json`, `replay_plan_summary.json`) plus `trace-lab replay-plan`. The replay plan is operator-checklist evidence only and does not execute replay, retry hidden actions, call hardware, or promote claims.

### v26 audit index

Adds `audit-index` for local artifact navigation and hash-oriented evidence-map summaries. The audit index is operator navigation only, not truth validation, replay, approval, hardware execution, or claim promotion.


## v27 validation recipe

Adds `validation-recipe`, `validation_recipe_manifest.json`, and `validation_recipe_summary.json` as a local command-checklist artifact. The recipe records validation commands without executing them and preserves the no hardware/no truth/no promotion boundary.
