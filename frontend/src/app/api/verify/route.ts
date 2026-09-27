import { parseVerification } from "@/lib/verification";

export const runtime = "nodejs";

const error = (code: string, status: number) =>
  Response.json({ code }, { status });

export async function POST(request: Request) {
  let claim: string;
  try {
    const body: unknown = await request.json();
    if (
      !body ||
      typeof body !== "object" ||
      !("claim" in body) ||
      typeof body.claim !== "string"
    )
      return error("INVALID_CLAIM", 400);
    claim = body.claim.trim();
    if (claim.length < 3 || claim.length > 1000)
      return error("INVALID_CLAIM", 400);
  } catch {
    return error("INVALID_CLAIM", 400);
  }

  let response: Response;
  try {
    const base = (
      process.env.LEXPROOF_API_URL || "http://127.0.0.1:8000"
    ).replace(/\/$/, "");
    response = await fetch(`${base}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ claim, retrieval_k: 8 }),
      cache: "no-store",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(120_000)]),
    });
  } catch {
    return error("SERVICE_UNAVAILABLE", 503);
  }
  if (!response.ok) {
    if (response.status === 400) return error("SOURCE_UNAVAILABLE", 503);
    return error("VERIFICATION_FAILED", 502);
  }
  try {
    const result = parseVerification(await response.json());
    if (result.claim !== claim) return error("INVALID_RESPONSE", 502);
    return Response.json(result, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return error("INVALID_RESPONSE", 502);
  }
}
