# OSLLM answer and universal-knowledge fix

## What changed
1. Strengthened streamed-output filtering for ordinary-prose planning leaks such as `Hmm...`, `Important to note`, `I recall from Source`, `For the explanation structure`, numbered response plans, and `Must avoid` checklists.
2. Strengthened both the runtime system prompt and the Ollama `Modelfile`: answer the OS question directly, do not reveal internal planning, and do not treat course notes as a hard knowledge boundary.
3. Changed RAG retrieval to score all indexed chunks and reserve up to four context passages for `knowledge_base/universal/`, rather than allowing unrelated course-note hits to crowd them out.
4. Increased the default retrieval context to six chunks and universal-source allowance to four.

## Apply on Linux
1. Back up the current project folder.
2. Extract this ZIP into a new folder and copy personal course PDFs/notes into its `knowledge_base/my_files/` folder.
3. From the extracted `OSLLM` folder, run:
   `python fetch_sources.py`
   `python ingest.py`
   `ollama create osllm -f Modelfile`
4. Restart the app/backend so it imports the updated Python code. Use the project's normal launcher, e.g. `bash run.sh`.

Rebuilding `osllm` matters because the Ollama Modelfile's SYSTEM prompt is stored in the custom model. Re-indexing matters so downloaded universal reference documents are included in FAISS.

## Important
This is a local indexed reference fallback, not live web search on every question. The model can supplement missing details with general OS knowledge, but it should not fabricate citations. Evaluate the output with representative questions before relying on it for grading.
