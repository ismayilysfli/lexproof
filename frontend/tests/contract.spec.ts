import { test, expect } from "@playwright/test";
import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from "node:http";
import { POST } from "../src/app/api/verify/route";
import { getTimeComparison, parseVerification } from "../src/lib/verification";
import supported from "./fixtures/supported.json";
import contradicted from "./fixtures/contradicted.json";

async function withBackend(
  handler: (request: IncomingMessage, response: ServerResponse) => void,
  run: () => Promise<void>,
) {
  const server = createServer(handler);
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("No test port");
  const previous = process.env.LEXPROOF_API_URL;
  process.env.LEXPROOF_API_URL = `http://127.0.0.1:${address.port}`;
  try {
    await run();
  } finally {
    if (previous === undefined) delete process.env.LEXPROOF_API_URL;
    else process.env.LEXPROOF_API_URL = previous;
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
}

function request(claim = supported.claim) {
  return new Request("http://localhost/api/verify", {
    method: "POST",
    body: JSON.stringify({ claim, retrieval_k: 15 }),
  });
}

test("proxy fixes retrieval_k at 8, preserves verdict, and strips technical fields", async () => {
  await withBackend(
    (req, res) => {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", () => {
        expect(req.url).toBe("/verify");
        expect(JSON.parse(body)).toEqual({
          claim: supported.claim,
          retrieval_k: 8,
        });
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify(supported));
      });
    },
    async () => {
      const response = await POST(request());
      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.verdict).toBe(supported.verdict);
      expect(result.primary_evidence.text).toBe(
        supported.primary_evidence.text,
      );
      expect(JSON.stringify(result)).not.toMatch(
        /retrieval_score|entailment|verification_model|segment_number/,
      );
    },
  );
});

for (const [status, code] of [
  [400, "SOURCE_UNAVAILABLE"],
  [500, "VERIFICATION_FAILED"],
] as const) {
  test(`proxy sanitizes upstream ${status} errors`, async () => {
    await withBackend(
      (_req, res) => {
        res.statusCode = status;
        res.end("Sensitive stack trace");
      },
      async () => {
        const response = await POST(request());
        expect(await response.json()).toEqual({ code });
      },
    );
  });
}

test("proxy rejects malformed and mismatched results", async () => {
  for (const body of [
    "not json",
    JSON.stringify({ ...supported, primary_evidence: null }),
    JSON.stringify({ ...supported, claim: "wrong claim" }),
  ]) {
    await withBackend(
      (_req, res) => {
        res.end(body);
      },
      async () => {
        const response = await POST(request());
        expect(response.status).toBe(502);
        expect(await response.json()).toEqual({ code: "INVALID_RESPONSE" });
      },
    );
  }
});

test("proxy rejects blank and oversized claims without contacting the backend", async () => {
  for (const claim of ["  ", "a", "a".repeat(1001)]) {
    expect((await POST(request(claim))).status).toBe(400);
  }
});

test("proxy handles a disconnected backend without leaking its error", async () => {
  await withBackend(
    (req) => {
      req.socket.destroy();
    },
    async () => {
      const response = await POST(request());
      expect(response.status).toBe(503);
      expect(await response.json()).toEqual({ code: "SERVICE_UNAVAILABLE" });
    },
  );
});

test("time comparison requires the known primary-law wording and backend signal", () => {
  const result = parseVerification(contradicted);
  expect(getTimeComparison(result)).toEqual({
    claim: "24 hours",
    law: "72 hours",
    qualification: "where feasible",
  });
  expect(getTimeComparison({ ...result, document: "other.pdf" })).toBeNull();
  expect(
    getTimeComparison({
      ...result,
      primary_evidence: { ...result.primary_evidence, heuristics: {} },
    }),
  ).toBeNull();
  expect(
    getTimeComparison({
      ...result,
      primary_evidence: {
        ...result.primary_evidence,
        text: "Another provision contains 72 hours.",
      },
    }),
  ).toBeNull();
  expect(
    getTimeComparison({
      ...result,
      claim: "Report a personal data breach within 24 hours or 48 hours.",
    }),
  ).toBeNull();
});
