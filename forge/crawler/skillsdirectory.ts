// Pulls the top skills list from the Skills Directory API (free tier: 100 requests/day, 100 results/page).
const KEY = process.env.SKILLSDIRECTORY_API_KEY;
const BASE = "https://www.skillsdirectory.com/api/v1/skills";

export async function fetchTopSkills(total = 1000, sort: "stars" | "votes" = "stars") {
  if (!KEY) throw new Error("Set SKILLSDIRECTORY_API_KEY in .env");
  const results: unknown[] = [];
  for (let offset = 0; offset < total; offset += 100) {
    const res = await fetch(`${BASE}?sort=${sort}&limit=100&offset=${offset}`, { headers: { "x-api-key": KEY } });
    if (!res.ok) throw new Error(`Skills Directory ${res.status}: ${await res.text()}`);
    const body = await res.json();
    results.push(...body.data);
    if (!body.pagination?.hasNextPage) break;
  }
  return results;
}
