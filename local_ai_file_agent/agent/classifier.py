import json
from .llm import call_llm
from .config import TASK_REGISTRY, READ_MODES


def classify_task(user_input):
    prompt = f"""You are a task classifier for a local AI file-handling agent.
Analyse the user's request and return a single JSON object.

════════════════════════════════════════════════
AVAILABLE TASKS (in priority order — read carefully)
════════════════════════════════════════════════
{list(TASK_REGISTRY.keys())}

════════════════════════════════════════════════════════════════
CRITICAL DISAMBIGUATION RULES  (read BEFORE the individual rules)
════════════════════════════════════════════════════════════════

A) FILE EXISTS vs FILE DOES NOT EXIST
   - If the user names an EXISTING file and wants to CHANGE it → REWRITE_FILE
   - If the user wants code/content WRITTEN FROM SCRATCH with no existing file → GENERATE_CODE
   - If the user wants one or more new files SAVED TO DISK → CREATE_FILE
   - "write a function in main.py" → REWRITE_FILE (file exists)
   - "write a function for sorting" → GENERATE_CODE (no file mentioned)
   - "write a python script and save it" → CREATE_FILE

B) GENERATE_CODE IS ONLY FOR SCRATCH CODE WITH NO EXISTING FILE
   GENERATE_CODE must NOT be used when:
   - The user names an existing file → use REWRITE_FILE
   - The user wants a project or multiple files → use CREATE_FILE
   - The user asks about a file → use READ_FILE
   - The user wants to convert a file → use FILE_CONVERT
   GENERATE_CODE IS correct when:
   - User says "give me code for X", "generate a function that does X", "show me code for X"
   - No file is named, no existing file is implied
   - The output will be shown on screen (may or may not be saved)

C) "CREATE" WORD DISAMBIGUATION
   - "create a csv file with employee data" → CREATE_FILE (file creation with content)
   - "create a function for quicksort" → GENERATE_CODE (scratch code, no file implied)
   - "create a project structure for flask" → CREATE_FILE (multiple files, project)
   - "create a folder and put files in it" → CREATE_FILE

D) "WRITE" WORD DISAMBIGUATION
   - "write code for binary search" → GENERATE_CODE
   - "write to config.json" → REWRITE_FILE
   - "write a script and save as utils.py" → CREATE_FILE
   - "write a python file for data cleaning" → CREATE_FILE

E) READ vs EXPLAIN
   - "show me", "read", "open", "print", "display" → READ_FILE (read_mode=READ_ONLY)
   - "explain", "describe", "what does", "summarise", "understand", "tell me about" → READ_FILE (read_mode=READ_EXPLAIN)

F) REWRITE vs VALIDATE
   - "fix the errors in main.py" → REWRITE_FILE (user wants it fixed)
   - "check main.py for errors" → VALIDATE_FILE (user wants a report, not a fix)
   - "is config.json valid?" → VALIDATE_FILE
   - "update config.json to fix the error" → REWRITE_FILE

════════════════════════════════════════════════════════════════
TASK RULES WITH EXTENSIVE EXAMPLES
════════════════════════════════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 1: READ_FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to SEE or UNDERSTAND file contents. File must NOT be changed.

read_mode = READ_ONLY (just show contents):
  "read main.py"
  "open config.json"
  "show me data.csv"
  "print the contents of settings.yaml"
  "display utils.py"
  "can you show what's in employees.xlsx"
  "let me see file.txt"
  "output the contents of app.js"
  "what does the file say"
  "show me C:\\Users\\data\\report.csv"
  "read C:\\project\\main.py"

read_mode = READ_EXPLAIN (explain what file does/means):
  "explain main.py"
  "what does config.json do"
  "describe utils.py"
  "summarise this csv"
  "tell me about the data in employees.xlsx"
  "what is this script doing"
  "walk me through app.js"
  "what does this code do"
  "understand this file for me"
  "give me an overview of settings.yaml"
  "what is the purpose of classifier.py"
  "can you explain what this javascript does"

NEVER use READ_FILE when the user wants to change anything.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 2: REWRITE_FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to MODIFY an existing file. A filename is always mentioned.

Code/script changes:
  "add error handling to main.py"
  "fix the bug in utils.py"
  "refactor classifier.py"
  "update app.js to use async/await"
  "add a new function to helpers.py"
  "rename the variable in script.py"
  "remove the print statements from main.py"
  "modify config.py to add a new setting"
  "rewrite the for loop in main.py as a list comprehension"
  "add logging to app.py"
  "make the function in utils.py return a dict"
  "add type hints to classifier.py"
  "clean up the code in main.py"
  "fix the indentation in script.py"
  "update the import statements in app.py"

Data file changes:
  "sort data.csv by age"
  "remove duplicates from employees.xlsx"
  "filter rows in data.csv where age > 30"
  "add a new column to employees.csv"
  "rename the Name column to full_name in data.csv"
  "clean the data in report.xlsx"
  "update the values in config.json"
  "change the host in settings.yaml"
  "add a new key to package.json"
  "update the version in config.toml"
  "reorder columns in data.csv"
  "format the dates in report.csv"
  "fill null values in employees.xlsx"
  "lowercase all values in the name column of data.csv"
  "delete rows where status is inactive in data.csv"

Config/document changes:
  "change the database host in config.json"
  "update the log level in settings.yaml"
  "add a new route to app.js"
  "fix the CSS in styles.css"
  "update the title in index.html"
  "add a new section to README.md"
  "modify the SQL query in report.sql"

IMPORTANT: filename will always be present for REWRITE_FILE.
NEVER use REWRITE_FILE when no file is mentioned.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 3: DIFF_PREVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to PREVIEW changes WITHOUT saving them.

  "show me what would change if I sort data.csv"
  "preview the diff for rewriting main.py"
  "what would happen if I update config.json"
  "dry run the changes to app.py"
  "show the diff before modifying employees.csv"
  "what changes would be made to settings.yaml"
  "let me see the proposed edits to utils.py"
  "preview rewrite of main.py"
  "show changes without saving"
  "diff preview for data.csv"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 4: VALIDATE_FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to CHECK if a file is valid — NOT to fix it.

  "validate config.json"
  "check main.py for syntax errors"
  "is data.csv valid"
  "are there any errors in app.js"
  "check if settings.yaml is properly formatted"
  "verify the structure of employees.xlsx"
  "is this JSON valid"
  "check the SQL in query.sql"
  "any issues with my python file"
  "validate the HTML in index.html"
  "check my CSV file"
  "is config.toml correctly formatted"
  "syntax check on utils.py"
  "check for errors in my code"
  "is data.xml well-formed"
  "does report.csv have the right columns"
  "check if package.json is valid"

KEY DISTINCTION: "check for errors" = VALIDATE_FILE. "fix the errors" = REWRITE_FILE.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 5: GENERATE_CODE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants code SHOWN or GENERATED from scratch.
NO existing file is mentioned. Output MAY optionally be saved.

CORRECT uses — no file name mentioned, no existing file implied:
  "generate python code for quicksort"
  "write a function for binary search"
  "give me a Java class for a linked list"
  "show me code for bubble sort"
  "write SQL to find duplicate records"
  "generate javascript for form validation"
  "give me a TypeScript interface for a user object"
  "code for reading a CSV file in Python"
  "write C++ code for a stack"
  "give me a Go function for HTTP requests"
  "show me how to connect to MySQL in Python"
  "write a Ruby method to parse JSON"
  "generate PHP code for file upload"
  "give me HTML for a login form"
  "CSS for a responsive navbar"
  "write a regex for email validation"
  "code to send an email in Python"
  "generate a fibonacci function"
  "give me code for a REST API in Flask"
  "write me a bash script to backup files"

WRONG — do NOT use GENERATE_CODE for these (use the correct task):
  "add a function to main.py" → REWRITE_FILE (existing file)
  "create main.py with a sorting algorithm" → CREATE_FILE (save to disk)
  "write a python project with multiple files" → CREATE_FILE
  "generate a project scaffold" → CREATE_FILE
  "what does this code do" → READ_FILE
  "fix the code in utils.py" → REWRITE_FILE
  "validate the code in app.js" → VALIDATE_FILE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 6: CREATE_FILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants one or more NEW files created and SAVED TO DISK.
Covers: single files, multiple files, project scaffolds, datasets.

Single file creation:
  "create a python file for data cleaning"
  "make a config.json with database settings"
  "create a CSV file with sample employee data"
  "generate a README.md for my project"
  "create an HTML page for login"
  "make a settings.yaml file"
  "create a requirements.txt"
  "generate a sample dataset with 100 rows"
  "create a .env file with API keys"
  "make a Dockerfile"
  "create an index.html file"
  "generate a main.py file for a flask app"
  "create utils.py with helper functions"
  "make a package.json"
  "create a schema.sql file"

Multi-file / project scaffold:
  "create a flask project structure"
  "scaffold a react app"
  "generate a Django project layout"
  "create a folder with main.py and utils.py"
  "build a project with models, views, and controllers"
  "set up a Node.js project with basic files"
  "create a python package structure"
  "generate a microservice project scaffold"
  "create 3 csv files with different employee departments"
  "make a project with a config file and a main script"
  "build a directory structure for a data pipeline"
  "create a folder with 5 sample CSV files"
  "generate a complete Flask API project"
  "create project files for a machine learning pipeline"

KEY DISTINCTION from GENERATE_CODE:
  CREATE_FILE = new files SAVED TO DISK
  GENERATE_CODE = code SHOWN on screen (may optionally save one file)
  If user says "create a file" or "save it" or "put it in" → CREATE_FILE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 7: FOLDER_ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to understand what is INSIDE a folder/directory.

  "analyse this folder"
  "what's in my project directory"
  "explain the structure of this codebase"
  "summarise the files in the data folder"
  "what files are in C:\\Users\\project"
  "analyse the project"
  "inspect this directory"
  "give me an overview of the project"
  "what does this codebase contain"
  "explain all files in this folder"
  "analyse C:\\myproject"
  "scan this directory and tell me what's there"
  "what are all the files doing in my project"
  "break down my project structure"
  "explain the files in src/"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 8: BATCH_OPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to rename, delete, or move MULTIPLE files in bulk.

Rename:
  "batch rename all csv files in the data folder"
  "rename all files to add a prefix"
  "replace spaces with underscores in all filenames"
  "rename all log files from .log to .txt"
  "add date prefix to all report files"

Delete:
  "delete all log files in the logs folder"
  "remove all .tmp files"
  "delete old files from the archive"
  "clean up the temp directory"

Move:
  "move all csv files to the data folder"
  "move all images to the assets directory"
  "transfer files from temp to archive"
  "move all python files to src/"
  "relocate all reports to the output folder"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 9: FILE_CONVERT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to CHANGE A FILE'S FORMAT. One file in → one file out (different format).
IMPORTANT: Target format is the word AFTER "to", "as", "into", "convert to".

Data format conversions:
  "convert data.csv to json"
  "turn employees.xlsx into csv"
  "export report.csv as excel"
  "change config.yaml to json"
  "convert the csv to xlsx"
  "make data.json into a csv file"
  "turn this excel into json"
  "convert users.tsv to csv"
  "export the data as yaml"
  "change data.xml to csv"

Document/code conversions:
  "convert report.docx to pdf"
  "export main.py as pdf"
  "turn README.md into a Word document"
  "convert index.html to markdown"
  "make notes.txt into a pdf"
  "export the python file as html"
  "convert script.py to txt"
  "turn this json file into an html table"
  "convert data.csv into an html page"
  "make C:\\Users\\data\\merged.csv into a txt"
  "export config.yaml as toml"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 10: FILE_MERGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to COMBINE 2+ files into one output file.

Data merge:
  "merge sales.csv and customers.csv"
  "combine all csv files in the data folder"
  "join employees.xlsx and departments.xlsx"
  "concatenate report1.csv, report2.csv, report3.csv"
  "stack all json files into one"
  "merge multiple excel sheets into one file"
  "combine csv files with matching columns"
  "merge data1.csv and data2.csv into merged.csv"

Code merge:
  "merge utils.py and helpers.py into one file"
  "combine all python files in src/"
  "join models.js and controllers.js"
  "merge my java files"

Multi-sheet Excel:
  "combine csv files into one excel with multiple sheets"
  "put each csv file into a separate sheet"
  "merge files into a multi-sheet workbook"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 11: FILE_SEARCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to FIND files by name/pattern OR search INSIDE files for text.

Find by name:
  "find all csv files in the project"
  "locate files named report"
  "search for python files in src/"
  "find *.log files"
  "where is config.json"
  "find all files with .sql extension"
  "locate the main file"
  "search for files containing 'backup' in the name"

Grep / content search:
  "find files containing 'error'"
  "grep for TODO in the codebase"
  "search for 'database_host' across all files"
  "which files mention 'deprecated'"
  "find all files with import pandas"
  "search for 'password' in config files"
  "grep 'def process' across python files"
  "find files with 'localhost' in them"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 12: FILE_BACKUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User explicitly wants to BACKUP or COPY a file/folder.

  "backup main.py"
  "back up the data folder"
  "make a copy of config.json"
  "save a backup of employees.xlsx"
  "create a backup before editing"
  "archive the project folder"
  "duplicate settings.yaml"
  "copy data.csv to backup"
  "make a safe copy of the database file"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 13: ZIP_READ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to inspect, read, or extract from an EXISTING ZIP file.

  "open archive.zip"
  "what's in project.zip"
  "list the contents of backup.zip"
  "extract files from data.zip"
  "unzip archive.zip"
  "read the files inside project.zip"
  "show what's in the zip file"
  "extract main.py from archive.zip"
  "inspect backup.zip"
  "what files are in the zip"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 14: ZIP_CREATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to CREATE a new ZIP archive.

  "zip the project folder"
  "compress the data directory into a zip"
  "create a zip file with main.py and utils.py"
  "archive the src folder"
  "pack all csv files into a zip"
  "make a zip of the reports"
  "create a zip archive of my project"
  "zip these files: a.py, b.py, c.py"
  "compress and save as backup.zip"
  "create a flask project and zip it"
  "generate files and bundle into a zip"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 15: RECYCLE_BIN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to manage the recycle bin.

  "show recycle bin"
  "what's in the bin"
  "restore deleted files"
  "recover file from bin"
  "empty the bin"
  "show deleted files"
  "restore data.csv from bin"
  "list what's been deleted"
  "clear the recycle bin"
  "bring back the deleted file"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 16: SAVE_CONTENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User wants to SAVE content to a file.
The content can come from:
  a) Content pasted/typed directly in the prompt
  b) Content previously generated/shown by the agent

Style A — FILE: block(s) pasted directly:
  User sends:
    FILE: main.py
    def foo(): pass
    FILE: utils.py
    def bar(): return 1

Style B — inline content after save command:
  "save this as config.json"
  {{"host": "localhost"}}

  "write this to employees.csv"
  id,name,age
  1,Alice,30

  "store the following in app.py"
  from flask import Flask
  app = Flask(__name__)

Style C — referring to previously shown content:
  "save that as main.py"
  "write that to data.csv"
  "save the above as report.pdf"
  "save it as employees.xlsx"
  "put that in helpers.js"
  "save the generated code as solution.py"
  "save the output as result.json"

IMPORTANT:
  - filename: the target file mentioned by the user
  - instructions: what the user said about saving
  - If user sends FILE: blocks or inline content → SAVE_CONTENT
  - If no content at all and no existing agent output → ask user
  - Do NOT use GENERATE_CODE or CREATE_FILE when user is pasting their own content

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK 17: CHAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use when: User asks a general question with NO file operation.

  "what is machine learning"
  "how does quicksort work"
  "explain neural networks"
  "what is a linked list"
  "how do I use pandas"
  "what is the difference between CSV and JSON"
  "how does Python handle exceptions"
  "what is REST API"
  "help me understand recursion"
  "what does the zip function do in python"

NEVER use CHAT when there is a file mentioned or a file task to be done.

════════════════════════════════════════════════
GUARDRAIL FLAGS
════════════════════════════════════════════════
Set guardrail_flag only when you clearly detect:
  "delete_data"  → "delete rows", "remove entries", "drop records", "delete duplicates"
  "overwrite"    → user explicitly names a file they want to overwrite
  "bulk_delete"  → BATCH_OPS with a delete action
  ""             → anything else / when uncertain

════════════════════════════════════════════════
OUTPUT FORMAT — STRICT JSON ONLY, nothing else
════════════════════════════════════════════════

{{
  "task": "<TASK_NAME>",
  "filename": "<filename or path the user mentioned — empty string if none>",
  "instructions": "<rephrase the user request as a clear, precise, self-contained instruction>",
  "read_mode": "<READ_ONLY | READ_EXPLAIN | empty string>",
  "assumed_summary": "<one sentence starting with a verb: what the user wants to do>",
  "guardrail_flag": "<delete_data | overwrite | bulk_delete | empty string>"
}}

FIELD RULES:
- task: must be exactly one of the available task names above.
- filename: only the file/folder the user explicitly mentioned. Empty if none.
- instructions: complete and unambiguous. Include the language name for code tasks.
  If modifying a file, include the filename and what to change.
  If generating code, include the language and what to build.
- read_mode: only for READ_FILE. READ_ONLY to display, READ_EXPLAIN to explain.
- assumed_summary: e.g. "Sort employees.csv by age ascending" or "Generate Python code for binary search"
- guardrail_flag: conservative — only set when clearly a risk.

FINAL REMINDER — THE MOST COMMON MISTAKES:
  ❌ Classifying "write a function to sort data" as GENERATE_CODE when a file is mentioned → use REWRITE_FILE
  ❌ Classifying "create a python script and save it" as GENERATE_CODE → use CREATE_FILE
  ❌ Classifying "add error handling to main.py" as GENERATE_CODE → use REWRITE_FILE
  ❌ Classifying "explain main.py" as GENERATE_CODE → use READ_FILE with READ_EXPLAIN
  ❌ Classifying "what does this code do" as GENERATE_CODE → use READ_FILE with READ_EXPLAIN
  ❌ Using GENERATE_CODE when the user mentions an existing filename → use REWRITE_FILE
  ✅ GENERATE_CODE only when: no file named, code shown from scratch, no project structure

User input:
{user_input}
"""

    try:
        raw = call_llm(prompt).strip()

        # Strip markdown fences if model added them
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.strip().startswith("```")
            ).strip()

        # Try to extract JSON if there is surrounding text
        if not raw.startswith("{"):
            import re
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                raw = m.group(0)

        data = json.loads(raw)

        # Sanitise task
        if data.get("task") not in TASK_REGISTRY:
            data["task"] = "CHAT"

        # Sanitise read_mode
        if data.get("read_mode") not in READ_MODES:
            data["read_mode"] = ""

        # Ensure all keys exist
        for key in ("filename", "instructions", "assumed_summary", "guardrail_flag"):
            if key not in data:
                data[key] = ""

        # ── Post-classification safety fixes ──────────────────────────────
        # If GENERATE_CODE was chosen but a filename was extracted, it is
        # almost certainly REWRITE_FILE (existing file) or CREATE_FILE.
        # Apply a heuristic correction the LLM sometimes misses.
        import os
        task     = data["task"]
        filename = data.get("filename", "")
        instr    = data.get("instructions", "").lower()

        if task == "GENERATE_CODE" and filename:
            ext = os.path.splitext(filename)[1].lower()
            # If it looks like an existing-file operation → REWRITE_FILE
            modify_words = (
                "add", "fix", "update", "modify", "edit", "change", "remove",
                "refactor", "rename", "clean", "sort", "filter", "delete row",
                "append", "insert", "replace", "correct"
            )
            save_words = ("save", "create", "write to", "make a file", "store")
            if any(w in instr for w in modify_words):
                data["task"] = "REWRITE_FILE"
            elif any(w in instr for w in save_words):
                data["task"] = "CREATE_FILE"

        return data

    except Exception:
        return {
            "task":            "CHAT",
            "filename":        "",
            "instructions":    user_input,
            "read_mode":       "",
            "assumed_summary": "",
            "guardrail_flag":  "",
        }
