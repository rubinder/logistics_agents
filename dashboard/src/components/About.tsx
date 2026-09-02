import "./About.css";

/**
 * The short orientation note above the run replay: what the stations are and
 * what the reader is actually watching happen.
 */
export function AboutBlurb() {
  return (
    <aside className="about-blurb" role="note">
      <strong>What you&apos;re watching.</strong> An inbound shipment notification enters as a
      message. An orchestrator agent decomposes it, three specialists work the parts (inventory
      reconciliation against the purchase order, carrier tracking, exception detection), and a
      synthesis agent turns their findings into one structured decision: accept, hold, reroute, or
      escalate. Each station below is a real model call, traced for cost, latency and tokens. Switch
      to <strong>Log</strong> to read the agents&apos; own reasoning.
    </aside>
  );
}

/**
 * The long-form tab: what the project is for, how a shipment actually moves
 * through it, and how its output is measured.
 *
 * Deliberately free of scores, rankings and costs — the Eval Board on this
 * page renders those from data, and a number written into prose goes stale
 * the next time the eval is re-recorded.
 */
export function AboutExtended() {
  return (
    <article className="about panel">
      <section className="about-section">
        <h2>Why this exists</h2>
        <p>
          Most agent demos wire up a model and hope. This one treats agent output the way you would
          treat any other critical code path: measured, tested, and defended on every change. The
          logistics domain is a concrete, believable place to show that discipline: decisions have
          obvious right and wrong answers, and the failure modes are easy to describe.
        </p>
        <p>
          The multi-agent pipeline is the visible half. The real deliverable is the machinery around
          it that proves the agents are good and catches the moment they stop being good.
        </p>
      </section>

      <section className="about-section">
        <h2>The flow, end to end</h2>
        <ol className="about-flow">
          <li>
            <span className="about-step">Notification</span> A shipment notification arrives on a
            Kafka topic: what a supplier claims they sent, against which purchase order.
          </li>
          <li>
            <span className="about-step">Orchestrator</span> An agent decomposes it into subtasks
            and routes them across a fixed DAG. The routing is deterministic on purpose: the
            interesting judgment belongs in the specialists, not in unpredictable control flow.
          </li>
          <li>
            <span className="about-step">Specialists</span> Inventory reconciliation, carrier
            tracking and exception detection each read the facts they need from Postgres (purchase
            orders, stock levels and warehouse capacity, carrier events) and return a structured
            finding rather than prose.
          </li>
          <li>
            <span className="about-step">Synthesis</span> A final agent weighs those findings
            against a written decision policy and emits one typed decision: a label, the confirmed
            exceptions, recommended actions, a confidence and its reasoning.
          </li>
          <li>
            <span className="about-step">Trace</span> Every model call is captured as it happens
            (inputs, outputs, tokens, cost, latency) and persisted alongside the decision.
          </li>
          <li>
            <span className="about-step">This dashboard</span> A FastAPI service reads that back and
            this page replays the run node by node. The Trace tab is the pipeline; the Log tab is
            what the agents actually said.
          </li>
        </ol>
      </section>

      <section className="about-section">
        <h2>How it is evaluated</h2>
        <p>
          A labeled dataset of shipment scenarios pairs each notification with its expected
          outcome, one perturbation at a time: a short shipment, a late delivery, missing paperwork,
          damage, an unknown purchase order, a destination without the capacity to receive the
          goods. A drop in score therefore points at a specific behavior rather than a vague sense
          that quality moved.
        </p>
        <p>
          Grading is hybrid. Deterministic graders check the decision label, the precision and
          recall of the detected exception set, and whether the recommended actions cover what the
          scenario required. An LLM judge scores something arithmetic cannot: whether the reasoning
          is faithful to the evidence and free of invention. It is never shown the expected answer,
          so it grades reasoning rather than agreement. A weighted composite blends the two, with
          most of the weight on the deterministic side.
        </p>
        <p>
          Those scores are only worth anything if they are defended. Every model response is
          recorded once and replayed from a fixture cache afterwards, so the whole evaluation re-runs
          on every pull request (deterministically, with no API key and at no cost) and fails the
          build if any case scores below its committed baseline. Each recorded baseline is stamped
          with the dataset and rubric version that produced it, so a changed dataset cannot be
          quietly compared against stale expectations.
        </p>
      </section>

      <section className="about-section">
        <h2>Comparing models</h2>
        <p>
          The same dataset runs across model tiers, scoring quality against cost and latency
          together. Because every call is traced, a slower or pricier model has to earn its place on
          evidence rather than reputation. The Eval Board below reports the current standing.
        </p>
      </section>

      <section className="about-section">
        <h2>Running this in public</h2>
        <p>
          This page is open to the internet, which is its own engineering problem. Unless the status
          chip reads <strong>Live</strong>, what you are seeing is bundled sample data: a recorded
          run served straight from the browser bundle, so the dashboard is fully explorable without
          anyone spending a cent or touching a model.
        </p>
        <p>
          Live runs are guarded rather than trusted. A ledger enforces a hard monthly spend cap and
          accounts for spend before the call rather than after, so a failure cannot leak budget.
          Per-visitor and global rate limits sit in front of that, the default model is the cheap
          one, and the API key stays server-side in the parameter store: never in this page, never
          in the bundle.
        </p>
      </section>
    </article>
  );
}
