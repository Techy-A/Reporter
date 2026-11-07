// Save static HTML snapshots of Reporter's real screens for the design-kit gates.
//
// The gates measure files, and both portals sit behind sign-in. So this loads the REAL front ends
// (Vite dev servers) in Chrome, answers their /api calls with the sample data below (no account,
// no backend, no credentials), waits for the screen to settle, removes scripts and saves the DOM.
//
//   1. Start the UIs:  npm run dev --prefix frontend/admin   and   npm run dev --prefix frontend/portal
//   2. node design/harness/snapshot.mjs
//   3. node design/kit/scripts/<gate>.mjs design/harness/out/<screen>.html
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(here, "../kit/package.json"));
const { chromium } = require("playwright");
const OUT = join(here, "out");
mkdirSync(OUT, { recursive: true });

const ADMIN = "http://localhost:5171";
const PORTAL = "http://localhost:5172";
const now = Date.now();
const iso = (minAgo) => new Date(now - minAgo * 60000).toISOString().replace("Z", "");

// ---------------------------------------------------------------- sample data
const SICK = {
  policy_title: "Leave Policy", version: "2026-01", ref: "4.2", heading: "Sick leave",
  excerpt: "Employees get 6 days of sick leave per calendar year. Sick leave and casual leave can be clubbed together for a maximum of 5 consecutive working days. A medical certificate is needed for more than 2 consecutive days of sick leave.",
};
const CASUAL = {
  policy_title: "Leave Policy", version: "2026-01", ref: "4.1", heading: "Casual leave",
  excerpt: "Employees get 8 days of casual leave per calendar year, credited on 1 January. Casual leave cannot be carried forward to the next year and is not encashed.",
};
const meta = { used_llm: false, tokens_in: 0, tokens_out: 0, agent_steps: 0, tools_used: [] };
const employees = [
  { id: 1, name: "Priya Sharma", email: "priya@acme.co.in", is_interviewer: true, active: true, location: "Bengaluru", grade: "L2", employment_type: "Full-time" },
  { id: 2, name: "Arjun Mehta", email: "arjun@acme.co.in", is_interviewer: true, active: true, location: "Pune", grade: "L3", employment_type: "Full-time" },
  { id: 3, name: "Neha Gupta", email: "neha@acme.co.in", is_interviewer: false, active: true, location: "Bengaluru", grade: "L1", employment_type: "Full-time" },
  { id: 4, name: "Rohit Verma", email: "rohit.verma@acme.co.in", is_interviewer: false, active: true, location: "", grade: "", employment_type: "Contract" },
];
const tickets = [
  { id: 7, employee_name: "Neha Gupta", kind: "question", sensitive: false, status: "open", created_at: iso(54), updated_at: iso(54) },
  { id: 6, employee_name: "Rohit Verma", kind: "talk_to_hr", sensitive: false, status: "open", created_at: iso(180), updated_at: iso(170) },
  { id: 5, employee_name: "Neha Gupta", kind: "sensitive", sensitive: true, status: "answered", created_at: iso(300), updated_at: iso(240) },
];
const ADMIN_API = {
  "/api/setup/status": { setup_done: true },
  "/api/auth/me": { id: 1, email: "aryan@acme.co.in", role: "owner", mfa_enabled: true, active: true },
  "/api/helpdesk/stats": {
    questions_7d: 46, answered_without_hr_7d: 38, by_route_7d: { policy: 24, faq: 9, leave: 5, no_answer: 6, sensitive: 2 },
    helpful_rate: 0.86, open_tickets: 2,
    model: { configured: false, name: null, tools: true, max_steps: 4, context_tokens: 1800, embeddings: false, embed_model: null, calls_7d: 0, tokens_in_7d: 0, tokens_out_7d: 0, avg_steps: null },
  },
  "/api/tickets": tickets,
  "/api/tickets/7": { ...tickets[0], messages: [
    { sender: "employee", text: "Is 14 November a holiday at the Bengaluru office? It isn't on the list I have.", at: iso(54) },
  ] },
  "/api/policies": [
    { id: 1, title: "Leave Policy", version: "2026-01", effective_from: "2026-01-01", status: "active", locations: [], grades: [], employment_types: [], source_name: "leave_policy.md", clause_count: 8, embedded: 0, created_at: iso(3000) },
    { id: 2, title: "Remote work", version: "2026-03", effective_from: "2026-04-01", status: "active", locations: ["Bengaluru"], grades: [], employment_types: [], source_name: "wfh_bengaluru.pdf", clause_count: 5, embedded: 0, created_at: iso(2000) },
    { id: 3, title: "Leave Policy", version: "2026-07", effective_from: "2026-12-01", status: "draft", locations: [], grades: [], employment_types: [], source_name: "leave_policy_v2.md", clause_count: 9, embedded: 0, created_at: iso(60) },
  ],
  "/api/employees": employees,
  "/api/kpis": { invited: 18, booked: 11, zero_touch_pct: 82, reminders_sent: 24, no_shows_7d: 1, needs_attention: 2 },
  "/api/health": { database: true, channels: { whatsapp: false, telegram: true }, llm_configured: false, messaging_paused: false, candidates_without_consent: 0, simulator: false },
  "/api/rounds": [{ id: 1, role_title: "Customer Support Associate", round_name: "HR round", duration_min: 30, mode: "video", location: "https://meet.example/acme", window_start: iso(1440), window_end: iso(-8000), interviewer_ids: [1, 2] }],
  "/api/candidates": [
    { id: 11, round_id: 1, name: "Riya Verma", phone_masked: "+91 ••••••3210", channel: "telegram", status: "confirmed", booked_start: iso(-1500), interviewer_id: 1, needs_attention: false, bot_paused: false, last_message_at: iso(30) },
    { id: 12, round_id: 1, name: "Kabir Singh", phone_masked: "+91 ••••••8841", channel: "telegram", status: "needs_recruiter", booked_start: null, interviewer_id: null, needs_attention: true, bot_paused: false, last_message_at: iso(12) },
    { id: 13, round_id: 1, name: "Ananya Iyer", phone_masked: "+91 ••••••1902", channel: "telegram", status: "booked", booked_start: iso(-2900), interviewer_id: 2, needs_attention: false, bot_paused: false, last_message_at: iso(200) },
    { id: 14, round_id: 1, name: "Sneha Kulkarni", phone_masked: "+91 ••••••5567", channel: "telegram", status: "invited", booked_start: null, interviewer_id: null, needs_attention: false, bot_paused: false, last_message_at: null },
  ],
  "/api/evals": [
    { id: 1, question: "Can I club sick and casual leave?", expect_route: "policy", expect_policy_title: "Leave Policy", expect_ref: "4.2", must_include: "", as_location: "", as_grade: "", as_employment_type: "", last_passed: true, last_detail: "Passed", last_run_at: iso(20) },
    { id: 2, question: "My manager is harassing me", expect_route: "sensitive", expect_policy_title: "", expect_ref: "", must_include: "", as_location: "", as_grade: "", as_employment_type: "", last_passed: true, last_detail: "Passed", last_run_at: iso(20) },
    { id: 3, question: "Who handles referrals?", expect_route: "faq", expect_policy_title: "", expect_ref: "", must_include: "", as_location: "", as_grade: "", as_employment_type: "", last_passed: false, last_detail: "Expected faq, got no_answer", last_run_at: iso(20) },
  ],
};
const PORTAL_API = {
  "/api/me": { name: "Priya Sharma", email: "priya@acme.co.in", organisation: "Acme Support Services", is_interviewer: true },
  "/api/me/interviews": [
    { id: 42, candidate_first_name: "Kavya", role_title: "Junior Frontend Developer", round_name: "Round 1: Code review", start: iso(80), duration_min: 30, mode: "video", location: "https://meet.example/k", status: "booked" },
    { id: 43, candidate_first_name: "Riya", role_title: "Customer Support Associate", round_name: "HR round", start: iso(-45), duration_min: 30, mode: "video", location: "https://meet.example/r", status: "confirmed" },
    { id: 44, candidate_first_name: "Aman", role_title: "Customer Support Associate", round_name: "HR round", start: iso(-1500), duration_min: 45, mode: "in_person", location: "Acme Tower, 14th Main Rd, HSR Layout, Bengaluru", status: "booked" },
  ],
  "/api/tickets": [
    { id: 7, kind: "question", status: "answered", created_at: iso(300), updated_at: iso(60), messages: [] },
    { id: 6, kind: "talk_to_hr", status: "open", created_at: iso(2000), updated_at: iso(2000), messages: [] },
  ],
};

async function serve(page, table, overrides = {}) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const key = url.pathname;
    const body = overrides[key] ?? table[key] ?? (key.startsWith("/api/tickets") ? table["/api/tickets"] : null);
    if (body === undefined || body === null) return route.fulfill({ status: 404, json: { detail: "Not found" } });
    if (body === 401) return route.fulfill({ status: 401, json: { detail: "Not signed in" } });
    return route.fulfill({ status: 200, json: typeof body === "function" ? body(route.request()) : body });
  });
}

async function save(page, name, origin) {
  await page.waitForTimeout(700);
  const html = await page.evaluate((base) => {
    document.querySelectorAll("script").forEach((s) => s.remove());
    const b = document.createElement("base");
    b.href = base + "/";
    document.head.prepend(b);
    return "<!doctype html>\n" + document.documentElement.outerHTML;
  }, origin);
  writeFileSync(join(OUT, `${name}.html`), html);
  console.log(`saved ${name}.html`);
}

const browser = await chromium.launch({ channel: "chrome" });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });

// ---------------------------------------------------------------- admin
{
  const p = await ctx.newPage();
  await serve(p, ADMIN_API);
  for (const [path, name] of [["/", "admin-board"], ["/helpdesk", "admin-helpdesk"], ["/answers", "admin-answers"], ["/people", "admin-people"]]) {
    await p.goto(ADMIN + path);
    await p.waitForSelector(".page");
    if (name === "admin-helpdesk") { await p.click(".ticket-row"); await p.waitForSelector(".ticket-panel .thread"); }
    await save(p, name, ADMIN);
  }
}

// ---------------------------------------------------------------- employee portal
{
  const p = await ctx.newPage();
  await serve(p, PORTAL_API, {
    "/api/ask": (req) => {
      const body = JSON.parse(req.postData() || "{}");
      if (/harass/i.test(body.text || "")) return { kind: "sensitive", text: "This sounds important, so a person should handle it, not a bot. What you typed hasn't been saved or sent to any AI. You can contact the people below directly, or ask HR to reach out to you privately.", citations: [], actions: [{ id: "private_contact", label: "Ask HR to contact me privately", draft: "" }], contacts: [{ label: "Internal Committee (POSH)", value: "Meera Iyer · ic@acme.co.in · ext 2104" }, { label: "Tele-MANAS, free mental-health support (24×7)", value: "14416" }, { label: "Emergency", value: "112" }], event_id: null, meta };
      return { kind: "policy_quote", text: "Here's what your policy says:", citations: [SICK, CASUAL], actions: [{ id: "ask_hr", label: "Ask HR", draft: "" }], contacts: [], event_id: 9, meta };
    },
  });
  await p.goto(PORTAL + "/");
  await p.waitForSelector(".ask-head");
  await save(p, "portal-ask-empty", PORTAL);

  await p.goto(PORTAL + "/");
  await p.waitForSelector(".ask-head");
  await p.getByRole("button", { name: "Club sick + casual leave?" }).click();
  await p.waitForSelector(".slip");
  await p.fill('input[aria-label="Your question"]', "My manager keeps harassing me");
  await p.getByRole("button", { name: "Ask", exact: true }).click();
  await p.waitForSelector(".ask-sensitive");
  await save(p, "portal-ask-chat", PORTAL);

  await p.goto(PORTAL + "/interviews");
  await p.waitForSelector(".p-card2");
  await save(p, "portal-interviews", PORTAL);
}
{
  const p = await ctx.newPage();
  await serve(p, { ...PORTAL_API, "/api/me": 401 });
  await p.goto(PORTAL + "/");
  await p.waitForSelector(".p-form");
  await save(p, "portal-signin", PORTAL);
}

await browser.close();
