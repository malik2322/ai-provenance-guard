import uuid
from datetime import datetime, timezone

import gradio as gr

import config  # noqa: F401 — loads .env / validates key at import time
from models import ContentSubmission
from services.detection import run_pipeline
from services.confidence import score as confidence_score
from services.labels import generate_label
from services.audit import log_classification, get_log
from services.appeals import submit_appeal, ContentNotFoundError
from storage.store import save_submission


# ---------------------------------------------------------------------------
# Tab 1 — Content Submission
# ---------------------------------------------------------------------------

def classify_content(text: str, creator_id: str):
    text = (text or "").strip()
    creator_id = (creator_id or "").strip()

    if not text:
        return "", "**Error:** Text is required.", "", "", ""
    if not creator_id:
        return "", "**Error:** Creator ID is required.", "", "", ""

    detection = run_pipeline(text)
    attribution, confidence = confidence_score(detection)
    label = generate_label(attribution, confidence)

    content_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    submission = ContentSubmission(
        content_id=content_id,
        creator_id=creator_id,
        text=text,
        timestamp=timestamp,
        attribution=attribution,
        confidence=confidence,
        llm_score=detection.llm_score,
        stylometric_score=detection.stylometric_score,
        label=label,
        status="classified",
        llm_available=detection.llm_available,
    )
    save_submission(submission)
    log_classification(submission)

    pct = round(confidence * 100)
    if attribution == "likely_ai":
        badge = f"### AI-Generated &nbsp; · &nbsp; {pct}% confidence"
    elif attribution == "likely_human":
        badge = f"### Human-Written &nbsp; · &nbsp; {pct}% confidence"
    else:
        badge = f"### Uncertain &nbsp; · &nbsp; {pct}% confidence"

    llm_val = f"{detection.llm_score:.3f}" if detection.llm_score is not None else "unavailable"
    signals_md = (
        f"| Signal | Score |\n|--------|-------|\n"
        f"| LLM (Groq) | {llm_val} |\n"
        f"| Stylometrics | {detection.stylometric_score:.3f} |\n"
        f"| Combined | {round(0.6 * (detection.llm_score or detection.stylometric_score) + 0.4 * detection.stylometric_score, 3)} |"
    )

    return content_id, badge, f"> {label}", signals_md, content_id


# ---------------------------------------------------------------------------
# Tab 2 — Appeal
# ---------------------------------------------------------------------------

def submit_appeal_handler(content_id: str, reasoning: str):
    content_id = (content_id or "").strip()
    reasoning = (reasoning or "").strip()

    if not content_id:
        return "**Error:** Content ID is required."
    if not reasoning:
        return "**Error:** Creator reasoning is required."

    try:
        appeal_record, _ = submit_appeal(content_id, reasoning)
        return (
            f"**Appeal received.**\n\n"
            f"- Appeal ID: `{appeal_record.appeal_id}`\n"
            f"- Content ID: `{content_id}`\n"
            f"- Status: `under_review`\n"
            f"- Original attribution: `{appeal_record.original_attribution}`\n\n"
            f"A human reviewer will assess your submission alongside your reasoning."
        )
    except ContentNotFoundError:
        return f"**Error:** Content ID `{content_id}` not found."
    except Exception as e:
        return f"**Error:** Appeal failed — {e}"


# ---------------------------------------------------------------------------
# Tab 3 — Audit Log
# ---------------------------------------------------------------------------

def load_audit_log():
    entries = get_log(limit=50)
    if not entries:
        return []

    rows = []
    for e in entries:
        ts = e.get("timestamp", "")[:19].replace("T", " ")
        rows.append([
            ts,
            e.get("event_type", ""),
            e.get("content_id", "")[:8] + "…",
            e.get("creator_id", ""),
            e.get("attribution", ""),
            f"{round(e.get('confidence', 0) * 100)}%",
            e.get("status", ""),
            (e.get("appeal_reasoning") or "")[:60],
        ])
    return rows


# ---------------------------------------------------------------------------
# Tab 4 — Analytics
# ---------------------------------------------------------------------------

def load_analytics():
    entries = get_log(limit=500)
    classifications = [e for e in entries if e.get("event_type") == "classification"]
    appeals = [e for e in entries if e.get("event_type") == "appeal"]

    total = len(classifications)
    if total == 0:
        return "No submissions yet. Submit some content to see analytics.", [], []

    ai_count      = sum(1 for e in classifications if e.get("attribution") == "likely_ai")
    human_count   = sum(1 for e in classifications if e.get("attribution") == "likely_human")
    uncertain_count = sum(1 for e in classifications if e.get("attribution") == "uncertain")
    appeal_count  = len(appeals)
    avg_conf      = sum(e.get("confidence", 0) for e in classifications) / total

    summary = (
        f"### Detection Summary\n\n"
        f"| Metric | Value |\n|--------|-------|\n"
        f"| Total Submissions | {total} |\n"
        f"| Likely AI-Generated | {ai_count} ({round(ai_count/total*100)}%) |\n"
        f"| Likely Human-Written | {human_count} ({round(human_count/total*100)}%) |\n"
        f"| Uncertain | {uncertain_count} ({round(uncertain_count/total*100)}%) |\n"
        f"| Appeals Filed | {appeal_count} |\n"
        f"| Appeal Rate | {round(appeal_count/total*100) if total else 0}% |\n"
        f"| Average Confidence | {round(avg_conf*100)}% |\n"
    )

    attribution_data = [
        ["Likely AI", ai_count],
        ["Likely Human", human_count],
        ["Uncertain", uncertain_count],
    ]

    confidence_data = [
        [f"{e.get('timestamp','')[:10]}  {e.get('content_id','')[:6]}",
         round(e.get("confidence", 0) * 100)]
        for e in reversed(classifications[-20:])
    ]

    return summary, attribution_data, confidence_data


# ---------------------------------------------------------------------------
# Gradio Interface
# ---------------------------------------------------------------------------

with gr.Blocks(title="Provenance Guard") as demo:
    gr.Markdown(
        "# Provenance Guard\n"
        "AI content attribution for creative platforms. "
        "Submit text to classify its origin, appeal misclassifications, and review the audit trail."
    )

    with gr.Tabs():

        # ------------------------------------------------------------------
        with gr.Tab("Submit Content"):
            gr.Markdown("### Classify a piece of text")
            with gr.Row():
                with gr.Column(scale=2):
                    txt_input = gr.Textbox(
                        label="Text to classify",
                        placeholder="Paste a poem, story excerpt, or blog post…",
                        lines=8,
                    )
                    creator_input = gr.Textbox(
                        label="Creator ID",
                        placeholder="e.g. user-123 or poet-alice",
                    )
                    submit_btn = gr.Button("Classify", variant="primary")

                with gr.Column(scale=2):
                    content_id_out = gr.Textbox(label="Content ID (save this for appeals)", interactive=False)
                    verdict_out    = gr.Markdown(label="Verdict")
                    label_out      = gr.Markdown(label="Transparency Label")
                    signals_out    = gr.Markdown(label="Signal Scores")
                    appeal_prefill = gr.Textbox(visible=False)  # carries ID to appeal tab

            submit_btn.click(
                fn=classify_content,
                inputs=[txt_input, creator_input],
                outputs=[content_id_out, verdict_out, label_out, signals_out, appeal_prefill],
            )

        # ------------------------------------------------------------------
        with gr.Tab("Appeal a Decision"):
            gr.Markdown(
                "### Contest a classification\n"
                "If you believe your content was misclassified, paste the Content ID "
                "from your submission and explain why the classification is incorrect."
            )
            appeal_id_in  = gr.Textbox(label="Content ID", placeholder="Paste your content_id here…")
            appeal_txt_in = gr.Textbox(
                label="Your reasoning",
                placeholder="Explain why you believe the classification is incorrect…",
                lines=5,
            )
            appeal_btn    = gr.Button("Submit Appeal", variant="primary")
            appeal_result = gr.Markdown(label="Result")

            appeal_btn.click(
                fn=submit_appeal_handler,
                inputs=[appeal_id_in, appeal_txt_in],
                outputs=[appeal_result],
            )

        # ------------------------------------------------------------------
        with gr.Tab("Audit Log"):
            gr.Markdown(
                "### Structured audit trail\n"
                "Every classification and appeal is logged here. "
                "This is what a human reviewer would consult when assessing an appeal."
            )
            log_btn = gr.Button("Refresh Log")
            log_table = gr.Dataframe(
                headers=["Timestamp", "Event", "Content ID", "Creator", "Attribution", "Confidence", "Status", "Appeal Reasoning"],
                datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                interactive=False,
                wrap=True,
            )
            log_btn.click(fn=load_audit_log, inputs=[], outputs=[log_table])
            demo.load(fn=load_audit_log, inputs=[], outputs=[log_table])

        # ------------------------------------------------------------------
        with gr.Tab("Analytics"):
            gr.Markdown(
                "### Detection patterns\n"
                "Aggregate view of attribution outcomes, appeal rate, and confidence trends."
            )
            analytics_btn = gr.Button("Refresh Analytics")
            analytics_md  = gr.Markdown()
            with gr.Row():
                attr_chart  = gr.Dataframe(
                    headers=["Attribution", "Count"],
                    label="Attribution Breakdown",
                    interactive=False,
                )
                conf_chart  = gr.Dataframe(
                    headers=["Submission", "Confidence (%)"],
                    label="Confidence — Last 20 Submissions",
                    interactive=False,
                )

            analytics_btn.click(fn=load_analytics, inputs=[], outputs=[analytics_md, attr_chart, conf_chart])
            demo.load(fn=load_analytics, inputs=[], outputs=[analytics_md, attr_chart, conf_chart])


if __name__ == "__main__":
    demo.launch(server_port=7860, share=False, theme=gr.themes.Soft())
