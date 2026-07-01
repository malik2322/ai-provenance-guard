# Provenance Guard — Planning Document

> Written before any implementation code. All architectural and design decisions are made here first and serve as the reference for Milestones 3–5.

---

## Detection Signals

### Signal 1: LLM-Based Classification (Groq)

**What it measures:**
Holistic semantic and stylistic coherence of the text. The model is prompted to evaluate whether the writing reads as human or AI-generated based on tone, sentence flow, word choice patterns, consistency of register, and use of filler phrases common in AI output ("it is important to note," "furthermore," "in conclusion").

**Output format:**
A JSON object returned by the model: `{"ai_probability": 0.0–1.0, "reasoning": "..."}`.
The `ai_probability` value becomes `llm_score` — a float between 0 and 1 where 1 means the model is highly confident the text is AI-generated.

**Why it differs between human and AI writing:**
AI-generated text tends to be grammatically perfect, tonally consistent, and structurally predictable. It avoids slang, typos, and abrupt register shifts. Human writing is messier — it has personal voice, inconsistencies, and unexpected phrasing that reflects individual thought rather than statistical prediction.

**Blind spots:**
- Polished, formal human writing (academic papers, legal documents) may score as AI-like.
- AI text prompted to mimic human imperfections (intentional typos, casual tone) may score as human.
- Very short texts (under 30 words) give the model insufficient signal.
- The model's own training biases may affect what it considers "AI-like."

---

### Signal 2: Stylometric Heuristics (Pure Python)

**What it measures:**
Measurable structural properties of the text that differ statistically between human and AI writing. Three metrics are computed:

1. **Sentence-Length Coefficient of Variation (SL-CV):** Standard deviation divided by mean sentence length. AI text tends to have uniform sentence lengths; human writing varies more.
2. **Type-Token Ratio (TTR):** Unique words divided by total words. AI text often repeats anchor words and phrasing; human writing at the same length tends to use more diverse vocabulary.
3. **Punctuation Density:** Punctuation characters divided by total characters. AI text is often precisely punctuated; human writing varies — sometimes sparse, sometimes dense.

**Output format:**
Each metric is normalized to 0–1 (where 1 = more AI-like). The three scores are averaged into a single `stylometric_score` float.

Normalization formulas:
- `score_slcv = 1.0 - min(sl_cv, 1.0)` — low variance → high AI score
- `score_ttr = 1.0 - ttr` — low vocabulary diversity → high AI score
- `score_punct = 1.0 - min(punct_density / 0.10, 1.0)` — very sparse punctuation → high AI score; human writing typically sits between 4–10%

Edge cases:
- Single sentence (SL-CV undefined): treat as 0.5 (neutral)
- Empty or whitespace-only text: return 0.5 across all metrics
- Text under 20 words: flag as low-reliability, still return score but note it

**Why it differs between human and AI writing:**
AI-generated text follows more regular statistical patterns at the structural level — it is produced by a system that optimizes for coherent, well-formed output, which naturally produces low variance. Human writing reflects individual thought rhythms, mood, and habit, which produces more statistical noise.

**Blind spots:**
- Non-native English speakers writing formally may score AI-like on TTR and SL-CV.
- Poetry and literary prose with intentional repetition (anaphora, refrains) will score AI-like on TTR.
- Lightly edited AI text retains structural patterns even when semantics change.
- Technical writing (code documentation, legal text) has naturally low variance.

---

### Why Both Signals Together

The signals are independent in what they examine:
- Signal 1 understands meaning and context; it is expensive (API call) but semantically rich.
- Signal 2 ignores meaning entirely; it is free (pure Python) and structurally objective.

When both signals agree, confidence is high. When they disagree, the system reports uncertainty rather than forcing a verdict — which is the right behavior for a platform where false positives harm real creators.

---

### Combining Signals into a Single Confidence Score

**Formula:**
```
combined_score = (0.6 × llm_score) + (0.4 × stylometric_score)
```

LLM gets higher weight (0.6) because it captures semantic patterns that stylometrics miss entirely. Stylometrics gets 0.4 as an independent structural check.

**Fallback:** If the Groq API is unavailable (timeout, 429, parse failure), the system falls back to stylometrics only:
```
combined_score = stylometric_score
```
The response includes `"llm_available": false` to surface this degraded state.

---

## Uncertainty Representation

### What the Score Means

The `combined_score` represents the probability that the text is AI-generated, where:
- `1.0` = system is certain the text was AI-generated
- `0.0` = system is certain the text was human-written
- `0.5` = system has no useful signal either way

A score of 0.60 means: two independent signals, after weighting, lean AI but not strongly. The system should not confidently accuse — this is the uncertain zone.

### Threshold Design

| Score range | Attribution | Reasoning |
|-------------|-------------|-----------|
| > 0.70 | `likely_ai` | Both signals lean AI with enough margin |
| < 0.35 | `likely_human` | Both signals lean human with enough margin |
| 0.35 – 0.70 | `uncertain` | Signals disagree or margin is too small |

**Why asymmetric thresholds (0.35 vs 0.70)?**
A false positive — labeling a human creator's work as AI — is more harmful than a false negative on this platform. The wider uncertain zone (35 percentage points) reflects that asymmetry. The system gives human creators the benefit of the doubt at the margins.

### Confidence Reported to the User

The `confidence` value in the API response is not the raw `combined_score`. It is converted to a human-readable percentage that reflects the strength of the determination:

- For `likely_ai`: `confidence = combined_score` (already represents AI probability)
- For `likely_human`: `confidence = 1.0 - combined_score` (flip to human-probability)
- For `uncertain`: `confidence = 0.5 + abs(combined_score - 0.525)` (reflects how close to the boundary)

The label text uses `round(confidence * 100)` as a percentage (e.g., "78% confidence").

A score of 0.51 (uncertain, barely above 0.5) produces a reported confidence of ~51%, which looks meaningfully different in the label than a score of 0.68 (uncertain but pushing the boundary), which produces ~65%. This is intentional: the label conveys real uncertainty rather than false precision.

---

## Transparency Label Design

Three verbatim label variants, ordered by confidence level:

### Variant 1: High-Confidence AI (`likely_ai`, score > 0.70)

> "This content was likely generated with AI assistance. Our analysis detected patterns consistent with AI-generated writing with {pct}% confidence. If you are the creator and believe this is incorrect, you can submit an appeal for human review."

### Variant 2: High-Confidence Human (`likely_human`, score < 0.35)

> "This content appears to be human-written. Our analysis found natural variation in writing style consistent with human authorship, with {pct}% confidence. No attribution concern has been flagged."

### Variant 3: Uncertain (0.35 ≤ score ≤ 0.70)

> "Our system could not confidently determine whether this content is human-written or AI-generated ({pct}% confidence). The content has not been flagged. If you are the creator and have concerns, you may submit an appeal for human review."

**Design notes:**
- All three variants tell the reader what the system concluded and how confident it is.
- Variants 1 and 3 mention the appeal pathway because those are the cases where a human creator might be harmed.
- Variant 2 omits the appeal mention because there is nothing to appeal — a human verdict favors the creator.
- The phrase "has not been flagged" in Variant 3 is deliberate: it reassures creators in the uncertain zone that no action has been taken against their content.

---

## Appeals Workflow

### Who Can Submit an Appeal

Any creator who has a `content_id` from a prior submission. The API does not require authentication — the `content_id` itself serves as a possession-based token. In a production system this would require auth; this is noted as a known limitation.

### What Information an Appeal Requires

```json
{
  "content_id": "uuid-string",
  "creator_reasoning": "Free-text explanation from the creator"
}
```

### What Happens When an Appeal Is Received

1. System looks up the `content_id` in storage (returns 404 if not found).
2. The submission's `status` field is updated from `"classified"` to `"under_review"` in `submissions.json`.
3. An appeal event is written to the audit log with:
   - `event_type: "appeal"`
   - `appeal_reasoning`: the creator's text
   - The original `attribution` and `confidence` preserved for context
   - New `status: "under_review"`
4. API returns a confirmation with an `appeal_id` and the updated status.

Automated re-classification is not performed. A human moderator would use `GET /log` to see all submissions in `under_review` status and review the original scores alongside the creator's reasoning.

### What a Human Reviewer Would See

When a reviewer calls `GET /log`, they see entries like:

```json
{
  "event_type": "appeal",
  "content_id": "...",
  "creator_id": "poet-user-42",
  "attribution": "likely_ai",
  "confidence": 0.74,
  "llm_score": 0.80,
  "stylometric_score": 0.65,
  "label": "This content was likely generated with AI assistance...",
  "status": "under_review",
  "appeal_reasoning": "I wrote this myself. I am a non-native English speaker..."
}
```

This gives the reviewer both the system's evidence and the creator's counter-argument in one place.

---

## Anticipated Edge Cases

### Edge Case 1: Poetry with Simple, Repetitive Vocabulary

A poem using anaphora (repeated line openings) or a simple vocabulary for effect — such as a children's poem or a minimalist lyric — will score high on the TTR-based stylometric signal (low vocabulary diversity = AI-like). Combined with a formal AI-like tone the LLM might also penalize, this poem could receive a false `likely_ai` classification despite being entirely human-written.

**Why this happens:** The stylometric signal treats vocabulary repetition as a structural marker of AI text. It cannot distinguish between intentional literary repetition and the predictable repetition of an LLM.

**Mitigation in design:** The asymmetric threshold (0.35/0.70) means this poem needs a combined score above 0.70 to be labeled AI — it is more likely to land in uncertain. The appeal pathway is explicitly mentioned in uncertain labels.

---

### Edge Case 2: Formal Academic Writing by a Non-Native English Speaker

A non-native English speaker who writes in very structured, grammatically careful English will produce low sentence-length variance and high punctuation regularity — both AI-like signals. The LLM may also flag the writing as AI-like because it lacks the casual irregularities the model associates with human text.

**Why this happens:** The signals are calibrated against a default assumption of casual-to-moderate English writing. Formal registers and learned grammatical precision fall outside that assumption.

**Mitigation in design:** This is explicitly acknowledged as the spec hints at this exact case ("I am a non-native English speaker and my writing style may appear more formal"). The appeal flow is the primary remedy. This case is also documented as a known limitation in the README.

---

## Architecture

### Architecture Diagram

```
SUBMISSION FLOW
───────────────────────────────────────────────────────────────
  Client
    │
    │  POST /submit  {text, creator_id}
    ▼
┌─────────────────┐
│  Rate Limiter   │──429──▶ Client (Too Many Requests)
│  10/min 100/day │
└────────┬────────┘
         │ {text, creator_id}
         ▼
┌──────────────────────────────────────────────────────┐
│                  Detection Pipeline                   │
│                                                      │
│  ┌───────────────────┐    ┌────────────────────────┐ │
│  │ Signal 1: Groq LLM│    │ Signal 2: Stylometrics │ │
│  │ (semantic/holistic│    │ (structural/statistical│ │
│  │                   │    │                        │ │
│  │ → llm_score: 0–1  │    │ • SL-CV score          │ │
│  │   (1 = likely AI) │    │ • TTR score            │ │
│  └────────┬──────────┘    │ • Punct density score  │ │
│           │               │ → stylo_score: 0–1     │ │
│           │               └───────────┬────────────┘ │
│           └──────────────┬────────────┘              │
│                          ▼                           │
│               ┌─────────────────────┐                │
│               │  Confidence Scorer  │                │
│               │  0.6×llm + 0.4×sty  │                │
│               │  → combined: 0–1    │                │
│               └──────────┬──────────┘                │
└──────────────────────────┼───────────────────────────┘
                           │ (attribution, confidence)
                           ▼
               ┌───────────────────────┐
               │   Label Generator     │
               │  score > 0.70 → AI    │
               │  score < 0.35 → Human │
               │  else      → Uncertain│
               └───────────┬───────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
  │   Storage    │  │  Audit Log   │  │    API Response      │
  │ submissions  │  │  log.json    │  │ {content_id,         │
  │ .json        │  │  (append)    │  │  attribution,        │
  └──────────────┘  └──────────────┘  │  confidence,         │
                                       │  label,              │
                                       │  signals: {llm, sty}}│
                                       └──────────────────────┘

APPEAL FLOW
───────────────────────────────────────────────────────────────
  Client
    │
    │  POST /appeal  {content_id, creator_reasoning}
    ▼
┌──────────────────────────────────┐
│         Appeals Service          │
│  1. Lookup content_id ──404──▶ Client
│  2. Update status → under_review │
│  3. Create AppealRecord          │
│  4. Write to audit log           │
└──────────────┬───────────────────┘
               │
       ┌───────┴──────────┐
       ▼                  ▼
┌──────────────┐  ┌──────────────┐
│   Storage    │  │  Audit Log   │
│ .status →    │  │  event_type: │
│ under_review │  │  "appeal"    │
└──────────────┘  └──────────────┘
               │
               ▼
  API Response {appeal_id, status: "under_review", message}
```

### Architecture Narrative

**Submission flow:** A client POSTs text and a creator ID to `/submit`. The request first passes through Flask-Limiter (rate gate). If allowed, the text enters the detection pipeline, which runs Signal 1 (Groq LLM call) and Signal 2 (pure-Python stylometrics) in sequence. The confidence scorer combines the two scores with a 60/40 weighted average into a `combined_score`. The label generator maps that score to one of three attribution verdicts and produces the transparency label text. The result is persisted to `submissions.json`, written to the audit log, and returned to the client as JSON.

**Appeal flow:** A client POSTs a `content_id` (from a prior `/submit` response) and a free-text `creator_reasoning` to `/appeal`. The appeals service validates that the `content_id` exists, updates its status to `"under_review"` in storage, appends an appeal event to the audit log preserving the original scores and the creator's reasoning, and returns a confirmation with a new `appeal_id`.

---

## AI Tool Plan

### M3 — Submission Endpoint + First Signal (Groq)

**Spec sections to provide:** Detection Signals (Signal 1), Architecture diagram (submission flow only), Uncertainty Representation (output format of llm_score).

**What to ask for:**
1. Flask app skeleton with `POST /submit` route stub that accepts `{text, creator_id}`, generates a UUID `content_id`, and returns a hardcoded placeholder response.
2. `classify_text(text: str) -> float | None` function in `groq_client.py` that sends text to `llama-3.3-70b-versatile` with a system prompt instructing it to return only `{"ai_probability": 0.0–1.0, "reasoning": "..."}`, parses the JSON, and returns the float. Returns `None` on any exception.

**How to verify before wiring in:**
Call `classify_text()` directly with the "clearly AI" and "clearly human" spec test inputs. Expect `llm_score > 0.7` for the AI input and `llm_score < 0.4` for the human input. If the model returns prose instead of JSON, tighten the system prompt.

---

### M4 — Second Signal + Confidence Scoring

**Spec sections to provide:** Detection Signals (Signal 2 — all three metrics and normalization formulas), Uncertainty Representation (thresholds, weighting formula, fallback logic).

**What to ask for:**
1. `analyze_text(text: str) -> float` function in `stylometrics.py` that computes SL-CV, TTR, and punctuation density, normalizes each to 0–1, averages them, and handles edge cases (single sentence, short text, empty text).
2. `score(llm_score, stylo_score, llm_available) -> tuple[str, float]` function in `confidence.py` that applies the 60/40 weighting, maps to `likely_ai` / `likely_human` / `uncertain` using the 0.35/0.70 thresholds, and computes the reported confidence value.

**What to check:**
After generation, run both functions independently against all four spec test inputs. Print `llm_score`, `stylo_score`, `combined_score`, `attribution` side by side. The clearly-AI input must produce `combined_score > 0.70`. The clearly-human input must produce `combined_score < 0.35`. If the stylometric function produces nearly identical scores across all inputs, the normalization is broken — fix it before wiring in.

---

### M5 — Production Layer (Labels, Appeals, Rate Limiting, Audit Log)

**Spec sections to provide:** Transparency Label Design (all three verbatim variants + threshold table), Appeals Workflow (full workflow steps, storage updates, audit log schema), Architecture diagram (both flows).

**What to ask for:**
1. `generate_label(attribution: str, confidence: float) -> str` in `labels.py` that maps the three variants using the exact verbatim text from this document, substituting `{pct}` with `round(confidence * 100)`.
2. `POST /appeal` route and `submit_appeal()` service function following the four-step appeals workflow defined above.

**How to verify:**
- Transparency labels: call `generate_label()` with `("likely_ai", 0.82)`, `("likely_human", 0.22)`, and `("uncertain", 0.58)` — confirm all three verbatim variants appear correctly and the percentage substitution is accurate.
- Appeals: POST a real `content_id` from a prior `/submit` call; then call `GET /log` and confirm the appeal entry shows `status: "under_review"` and `appeal_reasoning` populated.
- Rate limiting: run the 12-request loop from the spec; confirm exactly 10 × 200 then 2 × 429.

---

## Stretch Feature Plan

### Ensemble Detection (planned)

Add a third signal to the stylometric pipeline: **Average Words Per Sentence (complexity proxy)**. AI text tends toward moderate complexity (12–18 words/sentence) with low variance. Very short or very long averages with high variance suggest human writing.

**Weighting with 3 signals:**

| Signal | Weight | Rationale |
|--------|--------|-----------|
| LLM (Groq) | 0.55 | Semantic; highest single-signal reliability |
| Stylometrics (SL-CV + TTR + punct) | 0.30 | Structural; three sub-metrics averaged |
| Sentence complexity (words/sentence) | 0.15 | Structural; complementary to SL-CV |

Update `planning.md` with this table before implementing the third signal.

---

## File Structure

```
ai201-project4-provenance-guard/
├── planning.md              ← this file
├── README.md
├── requirements.txt
├── .env                     ← gitignored
├── app.py                   ← Flask factory + limiter init + blueprint registration
├── config.py                ← all constants: thresholds, weights, paths, rate limits
├── models.py                ← dataclasses: ContentSubmission, AppealRecord, etc.
├── services/
│   ├── __init__.py
│   ├── groq_client.py       ← Signal 1: LLM classification
│   ├── stylometrics.py      ← Signal 2: structural heuristics
│   ├── detection.py         ← orchestrates both signals → DetectionResult
│   ├── confidence.py        ← weighted scoring + attribution mapping
│   ├── labels.py            ← transparency label generator
│   ├── appeals.py           ← appeal validation + status update
│   └── audit.py             ← structured append-only log
├── storage/
│   ├── __init__.py
│   └── store.py             ← load/save submissions.json
├── routes/
│   ├── __init__.py
│   ├── submit.py            ← POST /submit
│   ├── appeal.py            ← POST /appeal
│   └── log.py               ← GET /log
└── data/                    ← created at runtime, gitignored
    ├── submissions.json
    └── audit_log.json
```

---

## Rate Limiting Rationale (Pre-Implementation Decision)

**Chosen limits:** 10 requests per minute, 100 requests per day.

**Reasoning:**
- A legitimate creator submitting a single poem, story, or blog post does not need more than 2–3 submissions in a sitting (draft → revision → final). 10 per minute is generous for legitimate bursts.
- 100 per day comfortably covers a prolific creator submitting 10–20 pieces per day with retries.
- An adversary attempting to flood the system (to generate noise in the audit log or probe classification boundaries) would be blocked after 10 rapid requests. The 429 response does not reveal scoring details, so probing the boundary is not useful anyway.
- Groq's free tier has its own rate limits; the submission rate limiter also protects against burning through the Groq quota via accidental or malicious flooding.
