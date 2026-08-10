# 🎙️ FinVoice – AI Financial Support Voice Assistant

FinVoice is a voice-enabled financial assistance agent built as part of the **10 Days of Voice Agents** challenge. Powered by **Murf Falcon TTS** and **LiveKit real-time communication**, FinVoice delivers an ultra-low-latency, multilingual financial guidance system, fraud prevention education, and government scheme eligibility checks to Indian citizens.

[![Challenge](https://img.shields.io/badge/10%20Days%20of%20Voice%20Agents-Challenge-orange)](#-10-days-of-voice-agents--progress)
[![Murf Falcon](https://img.shields.io/badge/TTS-Murf%20Falcon-6366F1)](https://murf.ai/api/docs/text-to-speech/streaming)
[![LiveKit](https://img.shields.io/badge/Transport-LiveKit-002cf2)](https://docs.livekit.io)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](#-day-4--persistent-memory)
[![Financial Services](https://img.shields.io/badge/Domain-Financial%20Services-emerald)](#-day-5--financial-scheme-eligibility-tool)

---

## 🌟 What is FinVoice?

FinVoice is a voice-first assistant designed to bridge the digital and financial literacy gap for Indian citizens. 

*   **Voice-First Financial Assistance**: Natural voice conversations with low-latency streaming responses.
*   **General Financial Information**: Plain-language explanations of basic banking accounts, digital payments, and safe practices.
*   **Government Scheme Guidance**: Step-by-step information and eligibility criteria for key central welfare schemes.
*   **Multilingual Interaction**: Interactive conversations in English, Hindi (Romanized Hinglish), and Telugu (Romanized Tenglish) to align with regional demographics.
*   **Persistent Memory with User Consent**: Remembers caller names, preferences, and scheme interests across restarts.
*   **Tool-Based Financial Eligibility Checking**: Evaluates scheme qualification criteria on non-sensitive parameter inputs.

> [!IMPORTANT]  
> **Disclaimer & Scope Limit**: FinVoice provides general financial information and does not approve loans, perform transactions, or request sensitive financial credentials (such as PINs, OTPs, or passwords).

---

## ✨ Key Features

*   🎙️ **Real-time voice conversation** — High-speed, natural voice interactions with dual-direction audio streaming.
*   🌐 **Multilingual support** — Intelligent language switching and response output in Hinglish, Tenglish, or English.
*   🧠 **Persistent user memory** — Remembers returning callers and their context securely across backend restarts.
*   🔐 **Consent-based memory** — Only stores caller information after receiving explicit verbal/text permission.
*   🛡️ **Financial safety guardrails** — Proactively warns users and rejects saving if any sensitive information (OTP, PIN, passwords) is shared.
*   🔧 **Scheme eligibility tool** — Domain-specific checker that processes non-sensitive parameters.
*   💬 **Text chat** — Interactive typing option with direct conversational mirroring.
*   📊 **Live transcript** — Live text logs of the spoken exchange shown on the screen.
*   📱 **Responsive frontend** — Sleek Next.js frontend with beautiful live audio visualizers and light/dark theme toggle.
*   🔊 **Murf Falcon TTS** — Sub-100ms text-to-speech engine for lifelike voice synthesis.
*   ⚡ **LiveKit real-time communication** — WebRTC-powered low-latency pipeline for seamless audio transport.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    User([🎙️ User]) <-->|Audio Stream| FE[FinVoice Frontend]
    FE <-->|WebRTC| LK[LiveKit Server]
    LK <-->|Real-time Stream| Agent[AI Agent Session]
    
    subgraph Agent [AI Agent Session]
        STT[Deepgram STT]
        LLM[Gemini 3.5 Flash Lite]
        TTS[Murf Falcon TTS]
        
        STT --> LLM
        LLM --> TTS
        
        subgraph Memory Tools
            lookup[lookup_user]
            save[save_user_memory]
        end
        
        subgraph Financial Tool
            check[check_scheme_eligibility]
        end
        
        LLM <--> Memory Tools
        LLM <--> Financial Tool
    end
    
    Memory Tools <--> DB[(SQLite Database)]
    Financial Tool <--> Data[(Local Scheme Dataset)]
```

### Major Components

1.  **FinVoice Frontend**: Next.js & React SPA utilizing LiveKit Agents UI. Includes theme toggle (light/dark), customizable branding, and dynamic audio visualizer styles.
2.  **LiveKit Server**: Orchestrates WebRTC connections, enabling low-latency real-time voice and transcript delivery.
3.  **STT (Deepgram Nova-3)**: Converts streaming user voice inputs to text.
4.  **LLM (Gemini 3.5 Flash Lite)**: Handles reasoning, intent categorization, safety guardrails, and tool triggering.
5.  **Murf Falcon TTS**: Streams back high-fidelity voice responses with ultra-fast latency.
6.  **SQLite Database (`finvoice_memory.db`)**: Holds persistent, user-consented profile data.
7.  **Local Scheme Dataset (`schemes_data.json`)**: Embedded repository of official government scheme eligibility rules.

---

## 📅 10 Days of Voice Agents – Progress

| Day | Feature | Status |
|---|---|---|
| Day 1 | Voice Agent + Murf Falcon TTS | ✅ |
| Day 2 | Persona, Objectives & Guardrails | ✅ |
| Day 3 | Personalised Financial Services Frontend | ✅ |
| Day 4 | Persistent Memory with SQLite | ✅ |
| Day 5 | Financial Scheme Eligibility Tool | ✅ |

---

## 🧠 Day 4 – Persistent Memory

FinVoice implements SQLite-backed persistent memory to recognise returning callers and make conversations feel natural and contextual:

*   **SQLite Database**: Profile information is stored securely in `backend/finvoice_memory.db`.
*   **Stable User ID**: The frontend sends a persistent identifier mapped to the client session.
*   **`lookup_user()`**: Automatically checks for an existing profile at the start of each session.
*   **`save_user_memory()`**: Updates the database with the user's name, preferred language, and non-sensitive facts.
*   **Consent Before Saving**: The agent will explicitly ask: *"Would you like me to remember your name/language preference for future conversations?"* before storing any info.
*   **Returning Caller Recognition**: Greet returning users by name (*"Welcome back, Devi!"*) and auto-restore their preferred language.
*   **Memory Survival**: User profiles survive backend agent crashes or server restarts.

> [!WARNING]  
> **Privacy Guardrails**: FinVoice validates all data before writing to the SQLite database. If a user shares sensitive info (e.g. PIN, OTP, CVV, passwords, full account numbers), the memory tool rejects it and issues a security warning.

---

## 🔧 Day 5 – Financial Scheme Eligibility Tool

FinVoice includes a dedicated eligibility checker to assess whether a user qualifies for popular central welfare schemes.

### Tool API
`check_scheme_eligibility(scheme_name, age, occupation, income_range, purpose, is_farmer, has_girl_child, girl_child_age)`

### What it does
Checks whether the user matches the criteria for supported government financial schemes:
1.  **Pradhan Mantri Jan Dhan Yojana (PMJDY)**
2.  **Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)**
3.  **Atal Pension Yojana (APY)**
4.  **Sukanya Samriddhi Yojana (SSY)**
5.  **Pradhan Mantri MUDRA Yojana (PMMY)**
6.  **Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY)**
7.  **Pradhan Mantri Suraksha Bima Yojana (PMSBY)**

### When the tool is triggered
It is triggered automatically when the user asks a qualification-related question:
> *"Am I eligible for the Sukanya Samriddhi Yojana?"*  
> *"Can I get a Mudra loan to start a kirana shop?"*

### When it is NOT triggered
General information requests are answered directly by the LLM without invoking the tool, saving API cost and latency:
> *"What is a savings account?"*  
> *"How do fixed deposits work?"*

### Data Source
*   **LOCAL DATASET**: All checks run against the embedded [schemes_data.json](file:///c:/Users/mumma/OneDrive/Desktop/Agent/murf-livekit-starter/backend/src/schemes_data.json) dataset.
*   **Official Sources**: Data is sourced from official government portals (`pmjdy.gov.in`, `pmkisan.gov.in`, `myscheme.gov.in`, `nsiindia.gov.in`, `mudra.org.in`).
*   **Verification Date**: Verified on **August 10, 2026**.

### Tool Response & Safety
*   **No Raw JSON**: The tool returns structured JSON data, which the agent naturally translates into clear, spoken sentences.
*   **Failure Handling**: If the local database is corrupt/unreachable, or if `SIMULATE_ELIGIBILITY_FAILURE=true` is set, the tool returns a status block and the agent responds:  
    *"I'm unable to access the scheme information right now, so I don't want to give you an inaccurate eligibility answer. Please try again shortly."* (No hallucinated answers).
*   **Preliminary Status**: The agent always clarifies that eligibility checks provide general guidance and final approval rests with the lender or governing authority.

---

## 🎥 Day 5 Demo

1.  **Inquiry**: User asks, *"Am I eligible for Sukanya Samriddhi Yojana?"*
2.  **Intent Recognition**: FinVoice identifies that a government scheme eligibility check is required.
3.  **Execution**: The agent triggers `check_scheme_eligibility(scheme_name='Sukanya Samriddhi Yojana')`.
4.  **Information Gathering**: If required details (like whether the caller has a girl child and her age) are missing from the caller's database profile, the agent asks for them.
5.  **Output**: Once the parameters are loaded, the tool checks the rules and the agent speaks the response naturally.
6.  **Fallback**: If the data file is missing or failure is simulated, it falls back to the safety message gracefully.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Next.js 14** | Frontend application framework |
| **React & TypeScript** | User interface & type-safe state management |
| **Tailwind CSS** | Premium custom responsive styling |
| **LiveKit Agents SDK** | Real-time voice agent connection & pipeline orchestration |
| **Murf Falcon** | Text-to-Speech engine (en-IN-anusha voice) |
| **Google Gemini** | LLM reasoning & intent engine (gemini-3.5-flash-lite) |
| **Deepgram Nova-3** | Real-time speech-to-text recognition |
| **SQLite** | Persistent user profile storage |
| **Python 3.10+** | Backend agent environment (managed via `uv`) |

---

## 🔐 Financial Safety

FinVoice prioritizes the security of users. FinVoice will **NEVER**:
*   Ask for or store **OTP** (One-Time Password)
*   Ask for or store **ATM/UPI PIN**
*   Ask for or store **passwords** or credentials
*   Ask for bank **account numbers** or **debit/credit card numbers**
*   Request **Aadhaar** or **PAN** numbers
*   Promise or guarantee loan approvals
*   Perform financial transfers or transactions

If any sensitive term is spoken or typed, FinVoice alerts the user immediately and refuses to write it to memory.

---

## 🚀 Getting Started

### Prerequisites
*   **Python 3.10+** and **[uv](https://docs.astral.sh/uv/)** package manager.
*   **Node.js 18+** and **pnpm** package manager.
*   A LiveKit account and project credentials.

### Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/murf-ai/murf-livekit-starter.git
    cd murf-livekit-starter
    ```

2.  **Configure Environment**:
    Create `.env.local` in both `backend/` and `frontend/` (copied from their respective `.env.example`).
    Ensure the following keys are set:
    *   `LIVEKIT_URL`
    *   `LIVEKIT_API_KEY`
    *   `LIVEKIT_API_SECRET`
    *   `MURF_API_KEY`
    *   `DEEPGRAM_API_KEY`
    *   `GOOGLE_API_KEY`

3.  **Install Backend Dependencies**:
    ```bash
    cd backend
    uv sync
    uv run python src/agent.py download-files
    ```

4.  **Install Frontend Dependencies**:
    ```bash
    cd ../frontend
    pnpm install
    ```

### Running Locally

You can launch the frontend, backend, and LiveKit server simultaneously.

**Option A (All-in-one script)**:
From the root folder:
```powershell
# Windows
.\start_app.ps1

# macOS/Linux
chmod +x start_app.sh
./start_app.sh
```

**Option B (Separate terminals)**:
```bash
# Terminal 1: LiveKit server in dev mode
.\livekit-server.exe --dev

# Terminal 2: Python voice agent
cd backend && uv run python src/agent.py dev

# Terminal 3: Next.js frontend
cd frontend && pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) to start testing.

---

## 📂 Project Structure

```
murf-livekit-starter/
├── backend/                        # Python voice agent pipeline
│   ├── src/
│   │   ├── agent.py                # Main agent logic & tool registrations
│   │   ├── memory_db.py            # SQLite user memory API (Day 4)
│   │   ├── schemes_checker.py      # Qualification evaluation logic (Day 5)
│   │   └── schemes_data.json       # Government schemes database (Verified Aug 10, 2026)
│   ├── tests/
│   │   └── test_agent.py           # Integration & safety evaluation tests
│   ├── pyproject.toml              # Python dependency file (uv)
│   └── railway.toml                # Railway deployment configuration
├── frontend/                       # React / Next.js web dashboard
│   ├── app/
│   │   ├── page.tsx                # Main audio visualizer page
│   │   └── api/token/route.ts      # LiveKit token dispatch endpoint
│   ├── components/                 # UI components
│   │   ├── agents-ui/              # Voice visualizer widgets
│   │   └── app/                    # Theme managers & layout wrappers
│   ├── app-config.ts               # Color scheme and branding configuration
│   └── package.json                # Node dependencies (pnpm)
├── start_app.ps1                   # Windows startup script
├── start_app.sh                    # Unix startup script
├── TEST_CONVERSATIONS.md           # Evaluation test transcripts
├── RED_TEAM.md                     # Security & robustness reports
└── README.md                       # Project documentation
```

---

## 🧪 Testing

FinVoice supports tests for critical capabilities:

1.  **Voice conversation**: Verify the agent answers user inputs correctly.
2.  **Language switching**: Speak in Hinglish or Tenglish and confirm the agent responds in the same Romanized script.
3.  **Memory persistence**: Connect, share your name, consent to save, disconnect, reconnect, and confirm that the agent greets you by name.
4.  **Consent handling**: Say "No" when asked if it should remember your details, and check that no SQLite record is modified.
5.  **Financial safety guardrails**: Try sharing a dummy OTP (e.g. "my OTP is 482910") and verify the warning protocol triggers.
6.  **Eligibility tool trigger**: Ask "Am I eligible for Mudra loan?" and verify `check_scheme_eligibility` runs.
7.  **Normal question without tool**: Ask "What is UPI?" and verify it is answered conversationally without a tool run.
8.  **Data-source failure fallback**: Run with `SIMULATE_ELIGIBILITY_FAILURE=true` in `backend/.env.local`, ask a scheme question, and verify the graceful error message.

To run the automated agent test suite:
```bash
cd backend
uv run pytest
```

---

## 📸 Demo / Screenshots

Refer to the project's visual dashboard and visualizer components under `frontend/public/` for og-image styling.

![FinVoice Preview](frontend/public/opengraph-image-bg.png)

---

## 🚀 Future Improvements

*   **Expanded Scheme Integrations**: Add more regional state and central government schemes.
*   **Live Official API Connections**: Fetch real-time interest rates and rules from official bank APIs.
*   **Deeper Multilingual Speech**: Support native scripts (Devanagari, Telugu scripts) directly with compatible TTS engines.
*   **Forget-Memory Feature**: Allow callers to ask the agent to erase their stored profile completely ("Forget my details").
*   **Additional Domain Tools**: Add interest calculators, SIP calculators, and loan EMI estimators.

---

## 👨‍💻 Built For

Developed for the **10 Days of Voice Agents** challenge. Built with ❤️ using Murf Falcon + LiveKit.

#10DaysOfVoiceAgents  
#VoiceForBharat
