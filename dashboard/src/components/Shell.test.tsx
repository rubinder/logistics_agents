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
