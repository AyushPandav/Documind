# DocuMind 🧠📄

> **Enterprise-Grade Multimodal Document Intelligence & Hybrid Multi-Source RAG Platform**

DocuMind is an intelligent, privacy-first document intelligence and multi-source research assistant. It seamlessly combines local document ingestion (PDFs, Word docs, Excel spreadsheets, images) with live web search and real-time API intelligence into a single self-reflective RAG (Retrieval-Augmented Generation) pipeline.

---

## 🚀 Key Features Built to Date

### 1. 🔀 Hybrid Multi-Source Retrieval Architecture
- **Intelligent Query Router**: Automatically parses user query intent and routes to:
  - 📄 **Internal Documents**: Local Vector DB (dense embeddings) + BM25 keyword search.
  - 🌐 **Live Web Search**: Real-time web retrieval via DuckDuckGo (`ddgs`) without external API keys.
  - 🕐 **Live APIs**:
    - **System Clock & Calendar**: Real-time date, local time, and UTC time.
    - **Weather Service**: Live weather conditions and forecasts via `wttr.in`.
    - **Crypto & Financial Markets**: Real-time coin prices in USD & INR via CoinGecko.
    - **Forex Exchange Rates**: Real-time currency conversions via Open Exchange.
  - **Multi-Source Compound Querying**: Automatically splits questions like *"According to our 2024 annual report, what was the revenue, and what is the current Bitcoin price?"* into separate retrieval sub-tasks and fuses the evidence.

### 2. 🔄 Self-Reflective Corrective RAG Loop
- **Dual Hybrid Retriever**: Combines Cosine Similarity (`sentence-transformers/all-MiniLM-L6-v2`) and BM25 with Reciprocal Rank Fusion (RRF).
- **Query Decomposition & Adaptive Reformulation**: Decomposes complex comparative questions into sub-queries and broadens low-confidence searches across up to 2 corrective iterations.
- **Cross-Document Conflict Detection**: Scans retrieved chunks across documents to identify contradictory figures, policies, or dates and alerts the user.
- **Strict Evidence Grounding**: Instructs LLM to answer strictly from retrieved context and explicitly declare insufficient information rather than fabricating facts.
- **LLM Circuit Breaker**: Primary local inference with Ollama (`qwen2.5:3b-instruct` / fallback models) for ultra-low latency and zero cloud data leaks.

### 3. 📑 Multimodal Document Ingestion Pipelines
- **Large PDF Processing**: Extracts text and tables with `pdfplumber`, handles multi-page documents, and balances chunk distributions across large manuals.
- **Excel & Tabular Data (.xlsx, .xls, .csv)**: Parses rows, columns, data types, and multi-sheet workbooks. Generates automated data schema summaries.
- **Word Documents (.docx)**: Extracts formatted text, sections, and structural headers.
- **Image & Visual Document Intelligence**: Multimodal image processing powered by OpenAI CLIP embeddings (`clip-ViT-B-32`) and EXIF metadata extraction.
- **Privacy & FHE (Fully Homomorphic Encryption)**: Secure client/server encryption pipeline for confidential document processing.

### 4. 🎙️ AI Voiceover & Short Summary
- **Summarized Voice Engine**: Generates concise audio summaries for long, dense answers.
- **Mobile (Expo Go / Native)**: Native device speech synthesis via `expo-speech` with play/stop controls.
- **Web App**: Direct audio streaming via `window.Audio`.

### 5. 📱 Premium Mobile & Web Interface (React Native / Expo)
- **Inline Markdown Renderer**: Custom zero-dependency renderer supporting `###` headers, **bold**, *italics*, `` `code` ``, code blocks, lists, and quote blocks.
- **Interactive Source Badges & Chips**:
  - `[1]`, `[2]` inline citation chips in message text.
  - Visual source classification badges:
    - 📄 **Internal Document** (Cyan badge + Page number)
    - 🌐 **Live Web** (Sky Blue badge + Domain URL)
    - 🕐 **Current Data** (Emerald Green badge + Live timestamp)
  - Bottom-sheet evidence inspector (`SourceSheet`) with quote snippets, URLs, and relevance bars (`██████████░░ 87%`).
- **Document Management**: Multi-file selection, batch upload, live processing status (`QUEUED` ➔ `OCR` ➔ `CHUNKING` ➔ `INDEXED`).
- **Session Management**: Full conversation history with create, rename, switch, and delete session options.
- **Cross-Document Correlation**: Relatedness analyzer for comparing themes and schemas across multiple uploaded files.

---

## 🏗️ Architecture

```
                    ┌─────────────────────────┐
                    │       User Query        │
                    └────────────┬────────────┘
                                 │
                      Intelligent Router
                                 │
           ┌─────────────────────┼─────────────────────┐
           │                     │                     │
           ▼                     ▼                     ▼
    Document RAG            Web Search             Live APIs
   Vector DB + BM25         DuckDuckGo          Clock / Weather /
  (PDF / XLSX / DOCX)     (Real-Time Web)       Crypto / Forex
           │                     │                     │
           └─────────────────────┼─────────────────────┘
                                 ▼
                         Evidence Fusion
                                 │
                      Cross-Source Reranking
                                 │
                     Conflict & Sufficiency Guard
                                 │
                      Strict Grounded Context
                                 │
                         LLM Generation
                     (Ollama / Local Models)
                                 │
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
    Grounded Response                       Source Citations
   (Markdown + Audio)                     (Docs, Web, Live APIs)
```

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.12, async event loop)
- **Database & Cache**: SQLite with WAL mode (`app_cache.db`)
- **Embeddings & Search**: `sentence-transformers`, `torch`, `rank_bm25`, `clip`
- **Web & Live APIs**: `ddgs` (DuckDuckGo Search), `httpx`, CoinGecko, wttr.in, Open Exchange
- **Parsers**: `pdfplumber`, `pypdf`, `python-docx`, `openpyxl`, `PIL`, `pytesseract`
- **LLM Runtime**: Ollama (`qwen2.5:3b-instruct` / local circuit breaker)

### Frontend
- **Framework**: React Native + Expo (SDK 52, Expo Router)
- **Styling**: Vanilla React Native StyleSheet with custom dark Cyberpunk theme
- **Speech & Audio**: `expo-speech`
- **Icons**: `@expo/vector-icons` (Ionicons)
- **Network**: Fetch API with SSE (Server-Sent Events) streaming support

---

## ⚡ Quick Start

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
pip install ddgs duckduckgo_search httpx

# Start the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install

# Start Expo dev server
npx expo start --clear
```

Scan the QR code with **Expo Go** on Android/iOS or press `w` to run on the web.

---

## 🧪 Sample Prompts to Test

| Query Type | Example Prompt | Active Sources |
|---|---|---|
| **Hybrid Document + Web** | *"According to our company's uploaded annual report, what was the revenue, and what is the current Bitcoin price?"* | 📄 Document + 🪙 CoinGecko API |
| **Live Web Search** | *"What are the latest news updates on ISRO missions?"* | 🌐 DuckDuckGo Web Search |
| **Live Time & Calendar** | *"What is the current time and today's date?"* | 🕐 System Clock API |
| **Live Weather** | *"What is the current weather in Tokyo?"* | 🌤️ wttr.in Weather API |
| **Document Overview** | *"Summarize this document and describe its main structure."* | 📄 Local Vector DB / BM25 |
| **Spreadsheet Query** | *"How many rows are in the spreadsheet and what are the column headers?"* | 📄 Tabular Pipeline |
