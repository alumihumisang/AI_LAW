# SDKG_WEB

This folder is the web handoff package for the SDKG indictment generator.

It provides a small API-facing layer while reusing the research pipeline in
`new_kg/`.  Web developers should start here instead of reading the older
research scripts directly.

## Contents

- `api_server.py`: FastAPI server with `/health` and `/generate`.
- `web_indictment_generator.py`: single-case SDKG generation wrapper.
- `sample_generate_request.json`: de-identified request body for testing.
- `requirements.txt`: minimal API/runtime dependencies.

## Run

From the repository root:

```bash
pip install -r SDKG_WEB/requirements.txt
uvicorn SDKG_WEB.api_server:app --host 0.0.0.0 --port 8000
```

Then test:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/generate \
  -H 'Content-Type: application/json' \
  -d @SDKG_WEB/sample_generate_request.json
```

## Runtime Requirements

- Ollama server available at `http://localhost:11434/api/generate`.
- Model `gemma3:27b` installed.
- SDKG data files in `new_kg/`, especially `phase1_boolean_severity_v1.jsonl`
  and severity-tree outputs.

## Data Policy

Do not put real indictment Excel files, lawyer inputs, PDFs, `.env`, model
cache files, or generated batch outputs in this folder.  Use de-identified
examples only.
