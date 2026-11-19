import { describe, expect, it } from "vitest";
import { claims, validatePdf } from "./citeverify";
describe("PDF upload constraints", () => {
  it("accepts PDF files", () => expect(validatePdf({ name: "paper.pdf", size: 1024 })).toBe(""));
  it("rejects other extensions", () =>
    expect(validatePdf({ name: "paper.docx", size: 1024 })).toBe("Only .pdf files are supported"));
  it("allows the 25 MB boundary", () =>
    expect(validatePdf({ name: "paper.pdf", size: 25 * 1024 * 1024 })).toBe(""));
  it("rejects files above 25 MB", () =>
    expect(validatePdf({ name: "paper.pdf", size: 25 * 1024 * 1024 + 1 })).toBe(
      "Your PDF must be 25 MB or smaller",
    ));
});
describe("demo triage", () => {
  it("contains nine claims", () => expect(claims).toHaveLength(9));
  it("contains four supported claims", () =>
    expect(claims.filter((c) => c.status === "supported")).toHaveLength(4));
  it("contains two partially supported claims", () =>
    expect(claims.filter((c) => c.status === "partial")).toHaveLength(2));
  it("contains two unsupported claims", () =>
    expect(claims.filter((c) => c.status === "unsupported")).toHaveLength(2));
  it("contains one outdated claim", () =>
    expect(claims.filter((c) => c.status === "outdated")).toHaveLength(1));
});
