"""
Mermaid Renderer
================
Renders Mermaid.js diagrams inside Streamlit using st.components.v1.html.
Loads Mermaid from jsDelivr CDN (same CDN already whitelisted in this env).

Usage:
    from neuroalign.ui.mermaid import render_mermaid
    render_mermaid(mermaid_code_string)
"""

import streamlit.components.v1 as components


_MERMAID_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ margin: 0; background: transparent; font-family: sans-serif; }}
    .mermaid {{ width: 100%; }}
  </style>
</head>
<body>
  <div class="mermaid">
{code}
  </div>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{
      startOnLoad: true,
      theme: 'neutral',
      flowchart: {{ useMaxWidth: true, htmlLabels: true }},
    }});
  </script>
</body>
</html>
"""


def render_mermaid(code: str, height: int = 420) -> None:
    """Render a Mermaid diagram inline in Streamlit."""
    # Strip fences if the model included them
    clean = code.strip()
    if clean.startswith("```"):
        lines = clean.split("\n")
        clean = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])

    html = _MERMAID_TEMPLATE.format(code=clean)
    components.html(html, height=height, scrolling=True)
