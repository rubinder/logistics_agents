import { FIXTURE_BUDGET } from "./api/fixtures";
import { Shell } from "./components/Shell";

export default function App() {
  return (
    <Shell budget={FIXTURE_BUDGET} usingFixtures>
      <h1>Logistics Agents</h1>
    </Shell>
  );
}
