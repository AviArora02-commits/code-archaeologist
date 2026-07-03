import { render, screen } from "@testing-library/react";
import { ConnectForm } from "@/components/ConnectForm";

describe("ConnectForm", () => {
  it("renders the connect form with GitHub URL input", () => {
    render(<ConnectForm onConnected={() => {}} />);
    expect(screen.getByPlaceholderText("https://github.com/owner/repo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /connect & estimate ingest/i })).toBeInTheDocument();
  });
});
