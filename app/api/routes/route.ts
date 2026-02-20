import { NextResponse } from "next/server";

/* =========================================
   Mock Database (Replace Later)
========================================= */

const mockData = {
  total_evaluations: 1284,
  average_trust_score: 82.6,
  blocked_count: 94,
  warned_count: 132,
  allowed_count: 1058,
  trend: [
    { date: "2026-02-12", avg_trust: 76 },
    { date: "2026-02-13", avg_trust: 80 },
    { date: "2026-02-14", avg_trust: 79 },
    { date: "2026-02-15", avg_trust: 84 },
    { date: "2026-02-16", avg_trust: 88 },
    { date: "2026-02-17", avg_trust: 85 },
    { date: "2026-02-18", avg_trust: 90 },
  ],
};

/* =========================================
   GET Handler
========================================= */

export async function GET() {
  // simulate latency
  await new Promise((res) => setTimeout(res, 300));

  return NextResponse.json(mockData);
}