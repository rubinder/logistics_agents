# Milestone 7: Dashboard + Run Visualizer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Vite + React + TypeScript dashboard — the public "watch it think" showcase — that renders the multi-agent pipeline as an animated **routing-manifest rail** (each agent a station lighting up in its decision-state signal color as its trace streams in, ending in a decision stamp), plus a runs board, a budget-gated trigger panel, and an eval quality board comparing models. It consumes the M6 API, with a bundled fixture fallback so it renders standalone and tests deterministically.

**Architecture:** A single-page Vite/React/TS app under `dashboard/`. An `api` client wraps the M6 endpoints and falls back to bundled fixtures when the API is unreachable or `VITE_USE_FIXTURES=1`. A small design-token CSS layer encodes the control-room palette + the decision-state signal colors + the type system (self-hosted `@fontsource`). Components are presentational and driven by typed data. Verification is `npm run build` (green) + `vitest` smoke/component tests — not exhaustive RTL coverage.

**Design system (bind all UI tasks):**
- Colors: `--void:#0E1420`, `--panel:#161E2E`, `--panel-2:#1D2739`, `--line:#26324A`, `--ink:#E6ECF5`, `--muted:#8A98B3`, `--cyan:#4CC9F0` (structure/active). Signal (decision states): `--accept:#3DD68C`, `--hold:#F5B14C`, `--reroute:#6EA8FE`, `--escalate:#FF6B6B`.
- Type: display=`"Space Grotesk"`, body=`"IBM Plex Sans"`, data/mono=`"IBM Plex Mono"` (self-hosted via `@fontsource/*`).
- Radius 6px; hairline borders in `--line`; motion respects `prefers-reduced-motion`.

**Tech Stack:** Node 24, Vite 5, React 18, TypeScript 5, Vitest + @testing-library/react, @fontsource fonts. Consumes the M6 FastAPI service.

## Global Constraints

- Everything lives under `dashboard/` (its own `package.json`; separate from the Python project).
- The app must build (`npm run build`) and test (`npm run test -- --run`) with **no network** — the fixture fallback covers the API being down.
- No external runtime dependencies fetched at load (fonts are bundled via `@fontsource`), so it works served from static S3.
- Accessibility floor: visible keyboard focus, `prefers-reduced-motion` respected, semantic landmarks.
- Commit after every task with a `feat:`/`chore:`/`test:` prefix.

---

### Task 1: Vite + React + TS scaffold

**Files:**
- Create: `dashboard/package.json`, `dashboard/tsconfig.json`, `dashboard/tsconfig.node.json`, `dashboard/vite.config.ts`, `dashboard/index.html`, `dashboard/src/main.tsx`, `dashboard/src/App.tsx`, `dashboard/src/vite-env.d.ts`, `dashboard/src/setupTests.ts`, `dashboard/src/App.test.tsx`, `dashboard/.gitignore`

**Interfaces:**
- Produces: a building Vite app with a Vitest smoke test; `App` renders a top-level `<main>` with the product name.

- [ ] **Step 1: Scaffold the project**

Run from `dashboard/`:
```bash
cd dashboard
npm init -y
npm install react@^18 react-dom@^18
npm install -D vite@^5 @vitejs/plugin-react typescript @types/react @types/react-dom vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
npm install @fontsource/space-grotesk @fontsource/ibm-plex-sans @fontsource/ibm-plex-mono
```

Set `dashboard/package.json` `"scripts"` to:
```json
{
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "test": "vitest"
}
```
and add `"type": "module"`.

`dashboard/.gitignore`:
```
node_modules
dist
```

- [ ] **Step 2: Write config + a failing smoke test**

`dashboard/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`dashboard/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

`dashboard/vite.config.ts`:
```ts
/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/setupTests.ts"],
  },
});
```

`dashboard/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Logistics Agents — Operations</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`dashboard/src/vite-env.d.ts`:
```ts
/// <reference types="vite/client" />
```

`dashboard/src/setupTests.ts`:
```ts
import "@testing-library/jest-dom";
```

`dashboard/src/main.tsx`:
```tsx
import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

`dashboard/src/App.tsx`:
```tsx
export default function App() {
  return (
    <main>
      <h1>Logistics Agents</h1>
    </main>
  );
}
```

`dashboard/src/App.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the product name", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: /logistics agents/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Verify build + test pass**

Run: `cd dashboard && npm run build`
Expected: PASS (tsc + vite build produce `dist/`).
Run: `cd dashboard && npm run test -- --run`
Expected: PASS (1 test).

- [ ] **Step 4: Commit**

```bash
git add dashboard
git commit -m "chore: scaffold Vite + React + TypeScript dashboard with Vitest"
```

---

### Task 2: API types + client with fixture fallback

**Files:**
- Create: `dashboard/src/api/types.ts`, `dashboard/src/api/fixtures.ts`, `dashboard/src/api/client.ts`, `dashboard/src/api/client.test.ts`

**Interfaces:**
- Produces:
  - `types.ts` — TS interfaces mirroring the API JSON: `TraceRecord`, `Decision`, `ExceptionRecord`, `BudgetStatus`, `EvalReport`, `CaseResult`, `RunSummary`, `TriggerResult`, `DecisionLabel` union.
  - `fixtures.ts` — a sample run (`FIXTURE_RUN_ID`, its 5 traces, its decision), `FIXTURE_BUDGET`, `FIXTURE_SCENARIOS`, `FIXTURE_EVAL_REPORTS` (2–3 models).
  - `client.ts` — `Api` with `listRuns()`, `getTrace(id)`, `getDecision(id)`, `getBudget()`, `getScenarios()`, `triggerRun(scenarioId)`, `getEvalReports()`; each calls the API (`import.meta.env.VITE_API_BASE ?? ""`) and, on any fetch error OR when `import.meta.env.VITE_USE_FIXTURES === "1"`, returns the matching fixture. A `usingFixtures` flag it exposes.

- [ ] **Step 1: Write the types + fixtures + client**

(The implementer writes `types.ts` mirroring the API shapes exactly — `TraceRecord{run_id,node,input_json,output_json,latency_ms,tokens,cost_usd,model,created_at}`, `Decision{label,exceptions,recommended_actions,confidence,reasoning}`, `BudgetStatus{cap_usd,spent_usd,remaining_usd}`, `EvalReport{model,results,label_accuracy,mean_f1,mean_action_coverage,mean_judge,mean_composite,rubric_version,dataset_version,timestamp,git_sha}`, `CaseResult{case_id,model,label,score}`. `DecisionLabel = "ACCEPT" | "HOLD" | "REROUTE" | "ESCALATE"`.)

`fixtures.ts` provides one realistic run whose 5 traces are `orchestrator, inventory, carrier, exception, synthesis` (each with plausible cost/latency/tokens and JSON I/O), a `HOLD` decision with a `QUANTITY_MISMATCH` exception, a budget `{cap_usd:20, spent_usd:3.2, remaining_usd:16.8}`, scenarios `["clean","quantity-mismatch"]`, and eval reports for `claude-opus-4-8`/`claude-sonnet-5`/`claude-haiku-4-5` with differing `mean_composite`/`label_accuracy`.

`client.ts` fetch-with-fallback pattern:
```ts
async function withFallback<T>(fetcher: () => Promise<T>, fixture: T): Promise<T> {
  if (import.meta.env.VITE_USE_FIXTURES === "1") return fixture;
  try {
    return await fetcher();
  } catch {
    return fixture;
  }
}
```

- [ ] **Step 2: Write the failing test**

`dashboard/src/api/client.test.ts` — with `vi.stubGlobal("fetch", ...)`:
```tsx
import { afterEach, describe, expect, it, vi } from "vitest";

import { Api } from "./client";
import { FIXTURE_BUDGET } from "./fixtures";

afterEach(() => vi.unstubAllGlobals());

describe("Api", () => {
  it("returns parsed data on success", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ cap_usd: 5, spent_usd: 1, remaining_usd: 4 }), { status: 200 })));
    const budget = await new Api("").getBudget();
    expect(budget.remaining_usd).toBe(4);
  });

  it("falls back to fixtures when the API errors", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("network down"); }));
    const budget = await new Api("").getBudget();
    expect(budget).toEqual(FIXTURE_BUDGET);
  });
});
```

- [ ] **Step 3: Verify**

Run: `cd dashboard && npm run test -- --run` → PASS.
Run: `cd dashboard && npm run build` → PASS.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/api
git commit -m "feat: add typed API client with fixture fallback and sample data"
```

---

### Task 3: Design tokens + app shell

**Files:**
- Create: `dashboard/src/styles/tokens.css`, `dashboard/src/styles/base.css`
- Modify: `dashboard/src/main.tsx` (import fonts + css), `dashboard/src/App.tsx`
- Create: `dashboard/src/components/Shell.tsx`, `dashboard/src/components/BudgetMeter.tsx`, `dashboard/src/components/Shell.test.tsx`

**Interfaces:**
- Produces: the visual foundation — `tokens.css` (the design-system variables above), `base.css` (resets, type scale, focus styles, reduced-motion), a `Shell` (masthead with product name + a live/fixtures status chip + `BudgetMeter`, and a content grid), and `BudgetMeter` (a fuel-gauge bar showing spent/cap with remaining, colored by headroom).

- [ ] **Step 1: Write tokens + base css**

`tokens.css` defines `:root` with all the palette + type variables from the design system. `base.css` sets `body{background:var(--void);color:var(--ink);font-family:"IBM Plex Sans"...}`, a type scale (display uses `"Space Grotesk"`, mono uses `"IBM Plex Mono"`), `:focus-visible{outline:2px solid var(--cyan)}`, and `@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}`.

`main.tsx` imports the fonts + css:
```tsx
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./styles/tokens.css";
import "./styles/base.css";
```

- [ ] **Step 2: Write Shell + BudgetMeter + a failing test**

`Shell` renders a `<header>` masthead (product name in Space Grotesk, a status chip reading "LIVE" or "SAMPLE DATA", the `BudgetMeter`) and a `<main>` slot for children. `BudgetMeter` takes `{cap_usd, spent_usd, remaining_usd}` and renders a labelled bar (`IBM Plex Mono` figures) whose fill width = `spent/cap`, tinted `--accept` when remaining is healthy, `--hold` under ~25%, `--escalate` when exhausted.

`Shell.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Shell } from "./Shell";

describe("Shell", () => {
  it("shows the masthead and budget figures", () => {
    render(
      <Shell budget={{ cap_usd: 20, spent_usd: 5, remaining_usd: 15 }} usingFixtures>
        <div>content</div>
      </Shell>,
    );
    expect(screen.getByText(/logistics agents/i)).toBeInTheDocument();
    expect(screen.getByText(/sample data/i)).toBeInTheDocument();
    expect(screen.getByText(/15\.00/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Verify build + test**

Run: `cd dashboard && npm run test -- --run` → PASS.
Run: `cd dashboard && npm run build` → PASS.

- [ ] **Step 4: Commit**

```bash
git add dashboard/src/styles dashboard/src/components dashboard/src/main.tsx dashboard/src/App.tsx
git commit -m "feat: add control-room design tokens, app shell, and budget meter"
```

---

### Task 4: Run visualizer — the routing-manifest rail (signature)

**Files:**
- Create: `dashboard/src/components/RunRail.tsx`, `dashboard/src/components/Station.tsx`, `dashboard/src/components/DecisionStamp.tsx`, `dashboard/src/components/signal.ts`, `dashboard/src/components/RunRail.test.tsx`

**Interfaces:**
- Consumes: `TraceRecord[]`, `Decision`.
- Produces:
  - `signal.ts` — `labelColor(label: DecisionLabel): string` mapping to the signal CSS vars, and `NODE_ORDER = ["orchestrator","inventory","carrier","exception","synthesis"]`.
  - `Station` — one agent node: name, status (pending/active/done), and its trace metrics (cost `$`, latency `ms`, tokens) in mono; animates to "done" (a subtle pulse in the decision color) when its trace arrives; respects reduced-motion.
  - `DecisionStamp` — the terminal decision rendered as a stamp: the label large in its signal color with a stamped/outlined treatment, plus confidence and the exception chips.
  - `RunRail` — lays the 5 stations along a horizontal rail (connectors between them), reveals each station as traces stream in (drive off the passed `traces` array — the parent feeds it incrementally via SSE in Task 5; with a full array it renders complete), and ends in the `DecisionStamp`. Responsive: the rail stacks vertically on narrow screens.

- [ ] **Step 1: Write the components + a failing test**

`RunRail.test.tsx`:
```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FIXTURE_DECISION, FIXTURE_TRACES } from "../api/fixtures";
import { RunRail } from "./RunRail";

describe("RunRail", () => {
  it("renders a station per node and the decision stamp", () => {
    render(<RunRail traces={FIXTURE_TRACES} decision={FIXTURE_DECISION} />);
    for (const node of ["orchestrator", "inventory", "carrier", "exception", "synthesis"]) {
      expect(screen.getByText(new RegExp(node, "i"))).toBeInTheDocument();
    }
    expect(screen.getByText(/HOLD/)).toBeInTheDocument();
  });
});
```
(Export `FIXTURE_TRACES` and `FIXTURE_DECISION` from `fixtures.ts` if not already named so.)

- [ ] **Step 2: Verify build + test**

Run: `cd dashboard && npm run test -- --run` → PASS.
Run: `cd dashboard && npm run build` → PASS.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/components
git commit -m "feat: add routing-manifest run visualizer (rail, stations, decision stamp)"
```

---

### Task 5: Runs board + live run view (SSE replay) + trigger panel

**Files:**
- Create: `dashboard/src/components/RunsBoard.tsx`, `dashboard/src/components/TriggerPanel.tsx`, `dashboard/src/components/RunView.tsx`, `dashboard/src/hooks/useRunStream.ts`, `dashboard/src/components/RunView.test.tsx`
- Modify: `dashboard/src/App.tsx` (compose Shell + RunsBoard + RunView + TriggerPanel)

**Interfaces:**
- Produces:
  - `useRunStream(runId, api)` — a hook that fetches `getTrace(runId)` and replays the traces into state one-by-one on a short timer (so stations light up in sequence for the visualizer), plus fetches the decision; returns `{traces, decision, done}`. (Replays the persisted run — the "watch it think" animation over M6's replay SSE/trace endpoint.)
  - `RunsBoard` — a departures-board list of recent runs (`listRuns()`), selectable; the selected id drives `RunView`.
  - `RunView` — composes `useRunStream` + `RunRail` + a per-node trace detail table (input/output JSON, cost, latency, tokens in mono).
  - `TriggerPanel` — a scenario `<select>` + a "Dispatch run" button (disabled when the budget meter shows exhausted); on click calls `triggerRun`, then selects the new run. Shows the API's 429/402 messages inline.
  - `App` wires it all: loads budget + scenarios + runs on mount, holds the selected run id, renders the Shell with everything.

- [ ] **Step 1: Write the components/hook + a failing test**

`RunView.test.tsx` renders `RunView` with an `Api` in fixtures mode (`VITE_USE_FIXTURES` or an injected fixtures client) and asserts (via `findBy`, since the replay is async) that the stations and decision appear. Use fake timers or `findBy*` with a generous timeout to let the replay drain.

- [ ] **Step 2: Verify build + test**

Run: `cd dashboard && npm run test -- --run` → PASS.
Run: `cd dashboard && npm run build` → PASS.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src
git commit -m "feat: add runs board, live-replay run view, and budget-gated trigger panel"
```

---

### Task 6: Eval quality board

**Files:**
- Create: `dashboard/src/components/EvalBoard.tsx`, `dashboard/src/components/MetricBar.tsx`, `dashboard/src/components/EvalBoard.test.tsx`
- Modify: `dashboard/src/App.tsx` (add the EvalBoard section)

**Interfaces:**
- Consumes: `EvalReport[]` (`getEvalReports()`).
- Produces: `EvalBoard` — a per-model comparison "quality board": for each model, its `label_accuracy`, `mean_f1`, and `mean_composite` as labelled horizontal bars (`MetricBar`), plus the `rubric_version`/`dataset_version` provenance. Bars use the palette (composite in `--cyan`, accuracy/F1 in muted tones); values in mono. Sorted by `mean_composite` desc. No external chart lib — hand-built bars keep it self-contained and on-palette.

- [ ] **Step 1: Write the components + a failing test**

`EvalBoard.test.tsx` renders `EvalBoard` with `FIXTURE_EVAL_REPORTS` and asserts each model id and its composite value appear, and that models are ordered by composite desc (assert the DOM order of the model labels).

- [ ] **Step 2: Verify build + test**

Run: `cd dashboard && npm run test -- --run` → PASS (all dashboard tests).
Run: `cd dashboard && npm run build` → PASS.

- [ ] **Step 3: Commit**

```bash
git add dashboard/src
git commit -m "feat: add eval quality board comparing models by composite, accuracy, F1"
```

---

### Task 7: CI dashboard-build job

**Files:**
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Produces: a second CI job `dashboard` that installs node, runs the dashboard's build + tests. Independent of the Python `test` job.

- [ ] **Step 1: Add the job**

Append a `dashboard` job to `.github/workflows/ci.yml`:
```yaml
  dashboard:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: dashboard
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
      - run: npm ci
      - run: npm run test -- --run
      - run: npm run build
```
Note: `npm ci` requires a committed `dashboard/package-lock.json` — ensure it was committed in Task 1 (it is created by `npm install`). If it's gitignored, un-ignore it (only `node_modules` and `dist` should be ignored).

- [ ] **Step 2: Verify locally**

Confirm `dashboard/package-lock.json` is tracked (`git ls-files dashboard/package-lock.json` prints the path). Run the job's commands locally:
Run: `cd dashboard && npm ci && npm run test -- --run && npm run build`
Expected: all PASS. Read the YAML back; confirm well-formed.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add dashboard build + test job"
```

---

## Self-Review

**Spec coverage (Milestone 7 scope = spec §5 dashboard/viewer + §9 relevant, milestone 15.7):**
- Run visualizer: DAG renders with nodes lighting up, per-node I/O/latency/cost, decision (§5): Tasks 4 + 5 (`RunRail` + `useRunStream` replay + trace detail). ✅
- Live via SSE / replay stored runs (§5): Task 5 replays the persisted run (the "live" animation over M6's trace/SSE data); a true live-during-execution stream remains an M6/M8 enhancement. ✅ (replay)
- Eval views: per-model comparison, quality metrics (§5): Task 6. ✅
- Trigger panel: pick a scenario → run, quota-gated, budget meter (§5): Tasks 3 (`BudgetMeter`) + 5 (`TriggerPanel`). ✅
- Read-only static build (§5): Vite `dist/` (Task 1), no server. ✅
- Consumes the M6 API with a fixture fallback so it renders standalone: Task 2. ✅

Out of scope (correctly deferred): CORS on the API (M6 deferral — needed for the deployed cross-origin dashboard; add in M8 alongside the deploy config, or as a one-line M6 follow-up). True live-during-execution SSE (nodes stream as the pipeline actually runs) — M7 animates the *replay*, which is the same visual; wiring a live producer endpoint is an M8/enhancement item. Quality-over-time *trends across commits* need multiple historical `EvalReport`s (the provenance fields exist; the trend view is a later enhancement once a history accrues) — M7 ships per-model comparison.

**Placeholder scan:** No TBD/TODO. Tasks 2/3/4/5/6 specify components by responsibility + a concrete smoke test rather than full JSX (a deliberate adaptation for a large frontend — the interfaces, design tokens, fixture shapes, and tests pin the contract); the implementer writes idiomatic React to that contract, verified by build + test.

**Type consistency:** `types.ts` (Task 2) mirrors the M6 API JSON exactly and is consumed by every component. `signal.labelColor`/`NODE_ORDER` (Task 4) drive `Station`/`RunRail`. `useRunStream` (Task 5) returns `{traces, decision, done}` consumed by `RunView`→`RunRail`. `BudgetStatus` feeds `BudgetMeter` (Task 3) and gates `TriggerPanel` (Task 5). `EvalReport` feeds `EvalBoard` (Task 6). The CI job (Task 7) runs the same `npm run build`/`test` verified in every task.
