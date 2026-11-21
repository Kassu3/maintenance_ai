# Industrial Machinery AI Diagnostics & Maintenance Center

A real-time AI-powered diagnostic and maintenance assistant built with **Python** and **Streamlit** for the **Excavator HMI Simulator**. The system listens to live machine telemetry over **UDP (port 45456)** on the fly and combines a local **Ollama (`gemma2:2b`)** large language model with a **RAG (Retrieval-Augmented Generation)** maintenance manual to provide operators with immediate troubleshooting and repair instructions during fault conditions.

 **[Related Project: Heavy Industrial HMI & Physics Simulator](#)** *(Replace with your excavator repo link)*
 
 ---
 
 ## System Architecture
 
 ```text
 [Excavator Physics Simulator] ──( JSON via UDP Port 45456 )──► [Streamlit AI Diagnostic Center] 
                                                                      │ 
                                                                ┌───────────────┴───────────────┐ 
                                                                ▼                      ▼ 
                                            [Watchdog Safety Monitor]      [Ollama LLM (gemma2:2b)] 
                                            (1.0s Timeout -> E-STOP)        + RAG Maintenance Manual
```

---

## Key Features

* **Auto-Updating Live Telemetry:** Gauges (RPM, temperatures, hydraulic pressures, boom angles) refresh automatically every **0.5 seconds** using an isolated `@st.fragment` in Streamlit without freezing or reloading the entire UI.
* **Smart AI Maintenance Assistant:** Uses the local `gemma2:2b` model via Ollama to stream responses token-by-token, analyzing real-time sensor readings against a digital maintenance manual (RAG) to give actionable repair steps.
* **Active Emergency Stop (E-STOP) Watchdog:** Continuously monitors incoming UDP traffic. If the simulator connection drops or goes silent for more than **1.0 second** (e.g., due to an emergency stop or network loss), the application automatically forces an `EMERGENCY STOP ACTIVE` state and zeros out the gauges.
* **Chat History Reset:** Includes a quick UI reset button to clear conversation history between diagnostic test runs.

---

## Prerequisites & Installation

### 1. Install Required Python Libraries
```bash
pip install streamlit ollama
```
*(Note: If you use `streamlit-autorefresh` in your environment, include it as well: `pip install streamlit ollama streamlit-autorefresh`)*

### 2. Install and Download the Local AI Model (Ollama)
Ensure [Ollama](https://ollama.com) is installed and running in the background, then pull the lightweight `gemma2:2b` model from your terminal:
```bash
ollama pull gemma2:2b
```

---

## Usage & Testing

### 1. Start the Streamlit Diagnostic Center
```bash
streamlit run ai_diagnostic_agent.py
```
The dashboard will open in your browser at `http://localhost:8501`.

### 2. Start the Python/Qt Excavator Simulator
Launch the excavator physics simulator so live telemetry begins streaming to UDP port `45456`.

### Important Note on Testing Emergency Stop (E-STOP)
Because stopping the simulator's GUI leaves its background network thread running, follow these steps to test the Emergency Stop watchdog behavior:
1. Press the **EMERGENCY STOP (HÄTÄ-PYSÄYTYS)** button in the simulator's HMI.
2. Go to the simulator's terminal/console and terminate the background process with **`Ctrl + C`**.
3. The **Streamlit app immediately detects the heartbeat loss (> 1.0 s)**, resets the gauges to zero, and displays the red **EMERGENCY STOP ACTIVE** alert banner.
4. Ask the AI assistant *"What should I do now?"* (*"Mitä teen?"*) to receive step-by-step instructions from the maintenance manual on inspecting hydraulic leaks and performing an `E-STOP RESET`.