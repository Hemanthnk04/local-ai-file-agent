# 🧠 Local AI File Agent (Ollama Powered)

An autonomous AI agent that can read, analyze, convert, and manage local files using LLMs — fully offline with Ollama.

---

## 🚀 Features

* 📂 File reading, writing, and transformation
* 🔄 File format conversion (CSV, TXT, etc.)
* 🧠 Task classification and execution pipeline
* ⚙️ Modular architecture (easy to extend)
* 🛡️ Guardrails for safe file operations
* 🧩 Event-driven system (AgentBus)

---

## 🧠 How It Works

User Input → Classifier → Resolver → Tool Execution → Output

---

## 💻 Demo

**Input:**
Convert `data.csv` to Excel and summarize it

**Output:**
✔ Converted to `data.xlsx`
✔ Generated summary of contents

---

## ⚙️ Installation

```bash
git clone https://github.com/YOUR_USERNAME/local-ai-file-agent.git
cd local-ai-file-agent
pip install -r requirements.txt
python main.py
```

---

## 📁 Project Structure

```
agent/
core/
tools/
config/
main.py
```

---

## 🧪 Example Use Cases

* CSV → Excel conversion
* Code rewriting (Python ↔ Java)
* File summarization
* Multi-file operations

---

## 🧠 Development Approach

Built with the assistance of AI tools for faster iteration.
All architecture design, module separation, and system integration were implemented and validated manually.

---

## 🚀 Future Improvements

* Multi-step planning agent
* Memory-based task execution
* API interface for integration

---

## ⭐ If you find this useful, consider starring the repo!
