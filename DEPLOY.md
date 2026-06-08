# NeuroAlign AI — Deployment Guide

## Running locally (development)

### 1. Setup

```bash
git clone https://github.com/YOUR_USERNAME/neuroalign-ai
cd neuroalign-ai
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your OPENAI_API_KEY
```

### 2. Run the Streamlit UI

```bash
streamlit run app.py
# Opens at http://localhost:8501
```

### 3. Run the FastAPI server (n8n / REST API)

```bash
uvicorn api:app --reload --port 8000
# API docs at http://localhost:8000/docs  ← interactive Swagger UI
# Health check: GET http://localhost:8000/health
```

Run both simultaneously in two terminal tabs.

---

## FastAPI endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/modes` | List valid cognitive modes |
| POST | `/transform` | Main transformation endpoint |
| POST | `/transform/batch` | Transform up to 10 texts at once |
| POST | `/webhook/n8n` | n8n Webhook node compatibility |

### Example curl call

```bash
curl -X POST http://localhost:8000/transform \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The quarterly report indicates a 47% revenue increase...",
    "modes": ["attention", "numerical"],
    "reading_density": "low",
    "structure_level": "high",
    "visual_support": "high"
  }'
```

---

## n8n integration

### Setup
1. Install n8n: `npx n8n` or use n8n Cloud (free tier available)
2. Open n8n at http://localhost:5678
3. Go to Workflows → Import from File
4. Select `n8n_workflow.json` from this project
5. Make sure FastAPI is running on port 8000
6. Activate the workflow

### How the workflow works
```
Webhook trigger (POST /webhook/neuroalign-input)
    ↓
NeuroAlign FastAPI /transform
    ↓
IF success → Format output → Return response
         ↓
         Format error → Return error
```

The workflow exposes a webhook URL you can POST to from anywhere:
- Notion automation
- Email clients
- Other n8n workflows
- Make.com / Zapier (via HTTP module)

### Extending the workflow
After the "Format output" node, add:
- **Send Email** node → deliver adapted document to user
- **Slack** node → post to accessibility channel
- **Notion** node → save to a database page
- **Google Sheets** node → log readability metrics for research

---

## Streamlit Community Cloud (free hosting)

1. Push project to a **public** GitHub repository
2. Create `.streamlit/secrets.toml` locally (add to `.gitignore`):
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
3. Go to https://share.streamlit.io → connect your repo
4. Set main file: `app.py`
5. Add the secret under App Settings → Secrets
6. Click Deploy → get URL like `neuroalign.streamlit.app`

Note: Streamlit Cloud runs only `app.py`. For the FastAPI + n8n integration,
run locally or deploy to a VPS/Railway/Render (all have free tiers).

---

## .gitignore

```
.env
.streamlit/secrets.toml
data/chroma/
data/research.db
data/costs.db
__pycache__/
*.pyc
.DS_Store
venv/
```

---

## Demo recording tip

Record a 2-minute screen demo before the thesis defense:
1. Show Streamlit UI transforming a complex academic text
2. Show the readability metrics panel (before/after Flesch scores)
3. Show the n8n workflow executing via the API
4. Show the research dataset export

Tools: QuickTime (built into Mac) or OBS Studio (free).
