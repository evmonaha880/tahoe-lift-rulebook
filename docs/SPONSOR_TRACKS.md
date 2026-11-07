# Sponsor tracks and prize requirements

Nothing here is built yet. This is the reference for what each sponsor prize asks for, so decisions can be made against real criteria. Source: the event's partner guides and the Fetch.ai hackpack (read 2026-11-07). Cash is upside; the core build and the portfolio piece come first. See `DECISIONS.md` entries 15, 18 and 19.

## Prize table (from the participant guide)

| Prize | Award |
|---|---|
| Overall (1st / 2nd / 3rd) | $3,000 / $2,000 / $1,000 cash + Gemini API credits (5,000 / 2,000 / 1,000) + DeepMind swag + $500 MongoDB credits each |
| Best Use of Fetch.ai | $2,500 (1st) and $2,500 (2nd) cash |
| Best Use of Meta Model API | $5,000 cash |
| Best Use of Subquadratic | $5,000 + 5,000 API credits (1st); $1,000 + 1,000 API credits (2nd) |

Criteria for Meta and Subquadratic were **not published** in the material read. Whether one project can enter several sponsor prizes is **unconfirmed** (ask in Discord `#questions`).

## Fetch.ai: "Agents That Prove Their Work"
Track text names three starting points, one of which is this project: *agents that reconstruct the past, delivering behavioral evidence that clearly separates what was observed from what was inferred.* The hackpack also warns that the result "should be **more than a chatbot or a thin wrapper around an API**."

**Mandatory (all six):** (1) at least one agent registered on Agentverse; (2) Agent Chat Protocol (ACP) implemented; (3) discoverable and usable through ASI:One; (4) meaningful tool execution or multi-agent orchestration; (5) the whole primary workflow completes inside an ASI:One conversation; (6) public GitHub repo with run or test instructions.

**Judging weights (hackpack):** functionality and technical implementation 25% · use of Fetch.ai technology 20% (Agentverse registration, chat protocol, payment protocol) · innovation and creativity 20% · real-world impact and usefulness 20% · user experience and presentation 15%.

**Bonus:** multi-agent collaboration, Payment Protocol with a credible model, ASI Interactive Cards, error handling and recovery, real-time data, an agent that could keep running after the hackathon.

**Submission steps (two places, not one):**
1. Submit on the Cerebral Valley dashboard (the AIE submission).
2. **Also** register the submission through the AIE Code Summit ASI:One Submission Agent: https://asi1.ai/auth/signup?returnTo=%2Ffestival%2Faiesummit2026%2Fdashboard%3Futm_source%3Daiesummit%26skip_onboarding%3Dtrue . Full instructions: https://docs.google.com/document/d/1Wuh3hAOfdfAfRoo09Y6iyPVDD-TyCGeatIzEo6T8AvE . Walkthrough video: https://drive.google.com/file/d/1EDfKrM7l8soO-40eKkPYDAEkRUTwQKyf
3. The agent README must name each agent and its **address**, list extra resources, and carry both badges: `![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)` and `![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)`.
4. Fetch.ai asks for a **3 to 5 minute demo video**. The AIE submission asks for a **1 minute** video. Two cuts are needed.

**Build references:** 5-minute setup (`pip install uagents openai`, an ASI:One key from https://asi1.ai/developer, rename the agent and seed): https://docs.google.com/document/d/1_Tb76j7zlzodhTiofHX_uPuEIfrDuQ3QAyk7c4osrd4 · basic ASI:One-compatible agent: https://uagents.fetch.ai/docs/examples/asi-1 · multi-agent quickstarter: https://github.com/fetchai/innovation-lab-examples/tree/main/fetch-hackathon-quickstarter · chat-protocol agents: https://innovationlab.fetch.ai/resources/docs/examples/chat-protocol/asi-compatible-uagents · running a local agent through a mailbox: https://innovationlab.fetch.ai/resources/docs/agent-creation/uagent-creation#mailbox-agents · interactive cards: https://innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards · Agentverse MCP server: https://mcp.agentverse.ai/sse . The chat protocol is imported from `uagents_core.contrib.protocols.chat` (ChatMessage, TextContent, StartSessionContent, EndSessionContent, ChatAcknowledgement).

**Plan if we do it (not started):** an agent that answers "why did this lift hold, and will it today?" It must not be a thin wrapper: it should chain several tools (look up the matching rule in the rulebook; retrieve historical analog days with observed vs inferred labels; fetch live station readings and the forecast; report the rule's held-out accuracy), and handle a failed tool call gracefully. Start only if core results exist by about 2:30 PM.

## Meta Model API ($5,000)
- OpenAI-compatible. Base URL `https://api.meta.ai/v1`, model `muse-spark-1.3`, 1M-token context, structured JSON output, tool calling (from Meta's cookbook, https://github.com/meta-models/meta-model-cookbook/tree/main/01_api_fundamentals ). Free-tier limits per team: 2,400 requests and 800,000 tokens per minute.
- $100 credits per participant; **claims close Saturday Nov 7 at 3:00 PM PT**; needs a dev.meta.ai account with billing verified and the same email as the hackathon acceptance. The API is US-only, so keep a fallback model.
- **Key verified 2026-11-07:** the model list returns `muse-spark-1.3` (also 1.1, 1.2, image, voice and other models). No generation call has been made yet: credits had not arrived, and early calls can be charged to the card.
- Our use: an independent blind labeler of tweets, with structured output and an agreement score against the rule parser. The submission should state this role in one sentence with numbers.

## Subquadratic ($5,000 + credits)
- Docs https://docs.subq.ai/ . Base URL `https://api.subq.ai/v1`; the quickstart posts to `/v1/systemone` with model `subq-snap-1.1`, a `state` (the text to reason over) and `questions` (each with instructions and criteria per answer). It behaves like a long-context classifier. **Verified 2026-11-07:** a test call worked. Each question comes back as a score between 0 and 1 (`noul`, 0.99 on a clear wind-hold post) plus token usage (119 input tokens for a one-sentence post). Per-question scores can serve as confidence values in the rules ledger.
- Our use: load a whole winter of posts at once to discover wording templates, and classify posts as an independent reader. Report tokens used, templates found and agreement.

## Gemini / DeepMind and MongoDB
No separate prize. Overall prizes include Gemini and MongoDB credits. Not needed; use only if a third independent labeler becomes useful (the DeepMind guide lists `gemini-4-argon` and the Interactions API).
