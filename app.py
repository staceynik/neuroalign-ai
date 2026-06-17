"""
NeuroAlign AI — Streamlit UI
=============================
Human-facing interface. All pipeline logic lives in neuroalign/runner.py.
Run: streamlit run app.py
"""

import streamlit as st
from dotenv import load_dotenv

from neuroalign.runner import run_pipeline, PipelineInput, PipelineOutput
from neuroalign.ui.mermaid import render_mermaid
from neuroalign.metrics import flesch_label
from neuroalign.research_db import load_dataframe, export_csv, delete_last_session
from neuroalign.cost_tracker import total_cost_today

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NeuroAlign AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
  .main .block-container { max-width: 900px; padding-top: 2rem; }
  .stTextArea textarea { font-size: 15px; line-height: 1.7; }
  h1 { font-weight: 600 !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:

    # Cognitive modes
    st.markdown("## 🧠 Support Mode")
    st.caption("Choose one type of support.")

    selected_mode = st.radio(
        "Support",
        [
            "🎯 Attention Support",
            "📖 Reading Support",
            "🔲 Explicit Structure",
            "🔢 Numerical Reasoning"
        ],
        label_visibility="collapsed"
    )

    mode_map = {
        "🎯 Attention Support": "attention",
        "📖 Reading Support": "reading",
        "🔲 Explicit Structure": "structure",
        "🔢 Numerical Reasoning": "numerical"
    }

    modes = [mode_map[selected_mode]]

    # Advanced settings — collapsed by default
    with st.expander("⚙️ Advanced settings", expanded=False):
        reading_density = st.select_slider(
            "Reading density",
            options=["very low", "low", "medium", "high"], value="low"
        )
        structure_level = st.select_slider(
            "Structure level",
            options=["low", "medium", "high", "very high"], value="high"
        )
        visual_support = st.select_slider(
            "Visual support",
            options=["low", "medium", "high"], value="high"
        )
    # Set defaults when expander is collapsed
    if "reading_density" not in st.session_state:
        reading_density = "low"
        structure_level = "high"
        visual_support  = "high"

    st.divider()

    # Memory consent
    st.markdown("## 💾 Memory")
    memory_consent = st.checkbox(
        "Remember my preferences across sessions",
        value=False,
        help="Saves style preferences locally (ChromaDB). No text content stored."
    )

    st.divider()

    # Research consent + demographics
    st.markdown("## 📋 Research Study")
    st.caption("Optional. Helps the thesis dataset. All data is anonymous and local.")
    research_consent = st.checkbox("I consent to anonymous data collection", value=False)

    demographics = {}
    if research_consent:
        demographics["age_range"] = st.selectbox(
            "Age range", ["18-24", "25-34", "35-44", "45-54", "55+"],
            index=None, placeholder="Select..."
        )
        demographics["gender"] = st.selectbox(
            "Gender", ["F", "M", "Non-binary", "Prefer not to say"],
            index=None, placeholder="Select..."
        )
        demographics["education_level"] = st.selectbox(
            "Education", ["High school", "Bachelor", "Master", "PhD", "Other"],
            index=None, placeholder="Select..."
        )
        demographics["occupation_type"] = st.selectbox(
            "Occupation",
            ["Student", "Academic / Researcher", "Tech / Engineering",
             "Healthcare", "Creative / Arts", "Other"],
            index=None, placeholder="Select..."
        )
        demographics["self_declared_support_need"] = st.select_slider(
            "How much do you feel you need cognitive support right now?",
            options=["None", "A little", "Moderate", "High", "Very high"],
            value="Moderate",
            help="Replaces fatigue slider — focuses on support need rather than tiredness."
        )

    st.divider()
    st.caption("NeuroAlign AI — Thesis PoC\nNot a diagnostic tool.")

# ── Main panel ────────────────────────────────────────────────────────────────

st.title("NeuroAlign AI 🧠")
st.markdown("*Adaptive content transformer for cognitive accessibility.*")

tab_input, tab_output = st.tabs(["📥 Input", "📤 Output"])

with tab_input:
    raw_input = st.text_area(
        "Paste your content here:",
        height=320,
        placeholder="Paste an article, academic text, task list, or any complex content...",
    )

    uploaded = st.file_uploader("Or upload a .txt or .pdf file:",
                                 type=["txt", "pdf"], label_visibility="collapsed")
    if uploaded:
        if uploaded.type == "text/plain":
            raw_input = uploaded.read().decode("utf-8")
            st.success(f"File loaded: {len(raw_input)} characters.")
        else:
            try:
                from pypdf import PdfReader
                reader    = PdfReader(uploaded)
                raw_input = " ".join(p.extract_text() or "" for p in reader.pages)
                st.success(f"PDF loaded: {len(raw_input)} characters.")
            except ImportError:
                st.error("Install pypdf: pip install pypdf")

    if not modes:
        st.info("Select at least one support mode in the sidebar.")

    run = st.button("✨ Transform Content", type="primary",
                    disabled=(not raw_input.strip() or not modes))

# ── Run pipeline ──────────────────────────────────────────────────────────────

if run and raw_input.strip() and modes:
    inp = PipelineInput(
        text             = raw_input,
        modes            = modes,
        reading_density  = reading_density,
        structure_level  = structure_level,
        visual_support   = visual_support,
        memory_consent   = memory_consent,
        research_consent = research_consent,
        demographics     = demographics,
        source           = "streamlit",
    )

    with st.status("Running NeuroAlign pipeline...", expanded=True) as status:
        st.write("🧠 Profiler: building cognitive profile...")
        st.write("🔬 Analyzer: parsing content structure...")
        st.write("🔄 Transformer: rewriting content...")
        st.write("👁️ Visualizer: generating output and diagrams...")
        output = run_pipeline(inp)
        if output.status == "error":
            status.update(label=f"❌ Error: {output.error}", state="error")
        else:
            status.update(label="✅ Complete!", state="complete")

    st.session_state["output"] = output
    st.rerun()

# ── Output tab ────────────────────────────────────────────────────────────────

with tab_output:
    if "output" not in st.session_state:
        st.info("Run a transformation to see results here.")
        st.stop()

    output: PipelineOutput = st.session_state["output"]

    if output.status == "error":
        st.error(f"Pipeline error: {output.error}")
        st.stop()

    # Content analysis
    if output.content_analysis:
        with st.expander("🔬 Content Analysis", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Type:** {output.content_analysis.get('document_type','—')}")
                st.markdown(f"**Cognitive load:** {output.content_analysis.get('cognitive_load','—')}")
                st.markdown(f"**Topic:** {output.content_analysis.get('main_topic','—')}")
            with col2:
                for a in output.content_analysis.get("actions", []):
                    st.markdown(f"- {a}")
                for d in output.content_analysis.get("deadlines", []):
                    st.markdown(f"⏰ {d}")

    # Readability metrics
    rd = output.readability
    if rd:
        with st.expander("📊 Readability Analysis", expanded=True):
            st.caption("Flesch: higher = easier. Grade/Fog: lower = more accessible.")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Flesch Ease",
                      f"{rd.get('flesch_ease_after',0):.1f}",
                      f"{rd.get('flesch_ease_delta',0):+.1f}")
            c2.metric("Grade Level",
                      f"{rd.get('grade_level_after',0):.1f}",
                      f"{rd.get('grade_level_delta',0):+.1f}",
                      delta_color="inverse")
            c3.metric("Fog Index",
                      f"{rd.get('fog_after',0):.1f}",
                      f"{rd.get('fog_delta',0):+.1f}",
                      delta_color="inverse")
            c4.metric("Avg sentence",
                      f"{rd.get('sentence_len_after',0):.1f}w",
                      f"{rd.get('sentence_len_delta',0):+.1f}",
                      delta_color="inverse")
            st.caption(
                f"Before: *{flesch_label(rd.get('flesch_ease_before',0))}* "
                f"→ After: *{flesch_label(rd.get('flesch_ease_after',0))}*"
            )
            import csv, io
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(rd.keys()))
            writer.writeheader()
            writer.writerow(rd)
            st.download_button("⬇️ Export metrics CSV", buf.getvalue(),
                               "neuroalign_metrics.csv", "text/csv")

    st.divider()

    # Transformed content
    st.markdown("### 📄 Transformed Content")
    st.markdown(output.final_markdown)

    # Mermaid diagram
    if output.mermaid_diagram:
        st.divider()
        st.markdown("### 🗺️ Visual Map")
        render_mermaid(output.mermaid_diagram)

    # Chart data
    if output.chart_data and output.chart_data.get("data_points"):
        st.divider()
        st.markdown("### 📊 Data Summary")
        st.json(output.chart_data)

    # Cost panel
    cost = output.cost
    if cost:
        with st.expander("💰 Cost & tokens", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total cost",    f"${cost.get('total_usd',0):.5f}")
            c2.metric("Total tokens",  f"{cost.get('total_tokens',0):,}")
            c3.metric("Agent calls",   len(cost.get("per_agent",[])))
            c4.metric("Most expensive", cost.get("most_expensive_agent","—"))
            st.caption(f"Total cost today: ${total_cost_today():.4f}")

    st.divider()

    # Downloads
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button("⬇️ Download Markdown",
                           output.final_markdown, "neuroalign_output.md", "text/markdown")
    with col_b:
        if output.mermaid_diagram:
            st.download_button("⬇️ Download Mermaid",
                               output.mermaid_diagram, "neuroalign_diagram.mmd", "text/plain")

    # Research feedback — only shown if consent given AND save_research callable exists
    if research_consent and output.save_research:
        st.divider()
        st.markdown("### 📋 Research Feedback")
        st.caption("One row will be saved to the local SQLite dataset after you click Submit.")

        usefulness = st.select_slider(
            "How useful was this transformation?",
            options=[1, 2, 3, 4, 5], value=3,
            format_func=lambda x: {
                1:"1 — Not useful", 2:"2 — Slightly",
                3:"3 — Moderately", 4:"4 — Very useful", 5:"5 — Extremely"
            }[x]
        )
        feedback = st.text_area("Comments (optional, anonymous):", height=80,
                                placeholder="e.g. 'The bullet structure helped a lot'")

        col_s, col_d = st.columns(2)
        with col_s:
            if st.button("✅ Submit feedback", type="secondary"):
                output.save_research(subjective_usefulness=usefulness, open_feedback=feedback)
                st.success("Saved — thank you!")
        with col_d:
            if st.button("🗑️ Delete my last session", type="secondary"):
                delete_last_session()
                st.info("Deleted.")

    # Researcher export
    with st.expander("🔬 Research dataset export (thesis author only)", expanded=False):
        df = load_dataframe()
        if df.empty:
            st.info("No sessions collected yet.")
        else:
            st.dataframe(df, use_container_width=True)
            st.download_button("⬇️ Export full dataset CSV",
                               export_csv(), "neuroalign_dataset.csv", "text/csv")
            st.caption(f"{len(df)} sessions collected.")
