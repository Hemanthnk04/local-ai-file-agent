# 🧠 Local AI File Agent (Ollama Powered)

A modular AI agent for performing structured operations on local files using LLMs (via Ollama).
Designed with a task classification → resolution → execution pipeline.

---

## 🚀 Overview

This project implements a **local file-handling AI agent** that interprets user instructions and executes file-related tasks through a modular system.

It focuses on:

* structured task execution
* safe file handling (guardrails)
* extensibility for new tools

---

## ⚙️ Core Capabilities

### 📂 File Operations

* Read file contents
* Write or overwrite files
* Extract information from files

---

### 🔄 File Transformations

* Convert file content into different formats (where supported by implemented tools)
* Generate summaries of text-based files
* Rewrite or modify file content

---

### 🧠 Task Understanding

* Classifies user input into predefined task types
* Maps tasks to appropriate execution modules
* Supports single-step task execution

---

### 🧩 Modular Tool System

* File operations handled via dedicated modules (`file_io`, `folder_ops`, etc.)
* Easily extendable with new tools

---

### 🛡️ Safety & Validation

* Input validation before execution
* Guardrails to prevent unsafe or unintended file operations

---

### ⚙️ Local LLM Integration

* Uses Ollama for local model inference
* No dependency on external APIs
* Runs fully offline (once models are available locally)

---

## 🧠 How It Works

User Input
→ Task Classification
→ Task Resolution
→ Tool Execution
→ Output

---

## 📁 Project Structure

```id="x1a9kc"
agent/              # Core agent loop and orchestration
core/               # Classification, resolution, validation
tools/              # File and folder operations
config/             # Configuration files
main.py             # Entry point
```

---

## 💻 Example Usage

**Input:**
Summarize the contents of `report.txt`

**Output:**

* Reads the file
* Processes content via LLM
* Returns a concise summary

---

**Input:**
Rewrite a Python file for clarity

**Output:**

* Reads file
* Generates improved version
* Writes updated content

---

## ⚙️ Installation

```bash id="k9v2nz"
git clone https://github.com/YOUR_USERNAME/local-ai-file-agent.git
cd local-ai-file-agent
pip install -r requirements.txt
python main.py
```

---

## 🔧 Requirements

* Python 3.x
* Ollama installed and running locally
* Supported LLM model (e.g., llama, mistral, etc.)

---

## ⚠️ Limitations

* Primarily supports **single-step task execution**
* No long-term memory between tasks
* Multi-step planning is not implemented
* Performance depends on the local model used

---

## 🧠 Development Approach

AI tools were used to accelerate development,
but all system design decisions, module structure, and integrations were implemented and validated manually.

---

## 🚀 Future Improvements

* Multi-step task planning
* Context-aware memory
* Expanded file format support
* API interface for external integration

---

## 📌 Notes

This project is intended as a **modular foundation for building autonomous file-processing agents**, rather than a fully autonomous system.

---

## ⭐ Feedback

Suggestions and improvements are welcome.
