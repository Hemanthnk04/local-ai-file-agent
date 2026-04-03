import os
import re

# Extension → language label
CODE_LANG = {
    ".py": "python", ".pyw": "python",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java", ".cs": "csharp",
    ".cpp": "cpp", ".c": "c",
    ".go": "go", ".rb": "ruby", ".php": "php",
    ".sql": "sql", ".css": "css",
    ".html": "html", ".htm": "html",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".json": "json",
    ".xml": "xml", ".md": "markdown",
}

DATA_EXTS   = {".csv", ".tsv", ".xlsx", ".json", ".xml", ".yaml", ".yml"}
DOC_EXTS    = {".txt", ".md", ".pdf", ".docx", ".html", ".htm"}
CODE_EXTS   = set(CODE_LANG.keys()) - DATA_EXTS - DOC_EXTS

# Language-specific code generation conventions
_LANG_RULES = {
    "python": (
        "• Output ONLY valid Python code.\n"
        "• Use 4-space indentation.\n"
        "• Include imports at top.\n"
        "• Add docstrings to functions and classes.\n"
        "• Include if __name__ == '__main__': block where applicable.\n"
        "• Follow PEP8 style.\n"
    ),
    "javascript": (
        "• Output ONLY valid JavaScript (ES6+).\n"
        "• Use const/let (never var).\n"
        "• Use arrow functions where appropriate.\n"
        "• Use async/await for async operations.\n"
        "• Add JSDoc comments for functions.\n"
        "• Export functions/classes where needed.\n"
    ),
    "typescript": (
        "• Output ONLY valid TypeScript.\n"
        "• Add explicit types to all function params and return values.\n"
        "• Use interfaces or types for object shapes.\n"
        "• Use const/let, async/await, arrow functions.\n"
        "• Add JSDoc comments.\n"
        "• Export types, interfaces, and functions.\n"
    ),
    "java": (
        "• Output ONLY valid Java code.\n"
        "• Include a proper class declaration matching the filename.\n"
        "• Add a public static void main(String[] args) method if a runnable class.\n"
        "• Use proper access modifiers (public/private/protected).\n"
        "• Add Javadoc comments for public methods.\n"
        "• Import required packages at the top.\n"
        "• Use standard Java naming conventions (CamelCase classes, camelCase methods).\n"
    ),
    "csharp": (
        "• Output ONLY valid C# code.\n"
        "• Include proper namespace and class declarations.\n"
        "• Add a Main method if it is a standalone program.\n"
        "• Use proper access modifiers.\n"
        "• Add XML doc comments for public members.\n"
        "• Follow PascalCase for classes/methods, camelCase for fields.\n"
    ),
    "cpp": (
        "• Output ONLY valid C++ code.\n"
        "• Include necessary #include directives.\n"
        "• Use std namespace or explicit std:: prefix.\n"
        "• Add a main() function if it is a runnable program.\n"
        "• Use modern C++17 features where appropriate.\n"
        "• Add comments for functions.\n"
    ),
    "c": (
        "• Output ONLY valid C code.\n"
        "• Include necessary #include directives.\n"
        "• Add a main() function if it is a runnable program.\n"
        "• Use function prototypes for all functions.\n"
        "• Add comments for functions.\n"
    ),
    "go": (
        "• Output ONLY valid Go code.\n"
        "• Start with package declaration.\n"
        "• Import required packages.\n"
        "• Add a main() function in package main if runnable.\n"
        "• Follow Go naming conventions (CamelCase exported, camelCase unexported).\n"
        "• Add Go doc comments for exported functions.\n"
    ),
    "ruby": (
        "• Output ONLY valid Ruby code.\n"
        "• Use 2-space indentation.\n"
        "• Follow Ruby naming conventions (snake_case methods/variables).\n"
        "• Add RDoc comments for methods.\n"
        "• Use puts/p for output.\n"
    ),
    "php": (
        "• Output ONLY valid PHP code.\n"
        "• Start with <?php tag.\n"
        "• Use strict_types declaration where appropriate.\n"
        "• Follow PSR-12 coding standards.\n"
        "• Add PHPDoc comments for functions.\n"
    ),
    "sql": (
        "• Output ONLY valid SQL statements.\n"
        "• Use uppercase for SQL keywords (SELECT, FROM, WHERE, etc.).\n"
        "• End each statement with a semicolon.\n"
        "• Add comments (-- comment) to explain complex queries.\n"
        "• Use proper indentation for readability.\n"
        "• Specify table/column aliases where helpful.\n"
    ),
    "css": (
        "• Output ONLY valid CSS.\n"
        "• Use consistent 2-space indentation inside rules.\n"
        "• Group related properties together.\n"
        "• Add comments for sections.\n"
        "• Use class selectors over IDs where possible.\n"
    ),
    "html": (
        "• Output ONLY valid HTML5.\n"
        "• Include DOCTYPE, <html>, <head>, and <body> tags.\n"
        "• Add <meta charset='UTF-8'> and viewport meta tag.\n"
        "• Use semantic HTML elements (header, main, section, article, footer).\n"
        "• Ensure all tags are properly closed.\n"
    ),
    "bash": (
        "• Output ONLY valid shell script.\n"
        "• Start with #!/bin/bash shebang.\n"
        "• Add set -e to exit on errors.\n"
        "• Quote all variables: \"$VAR\".\n"
        "• Add comments for each major section.\n"
        "• Use functions for reusable logic.\n"
    ),
    "yaml": (
        "• Output ONLY valid YAML.\n"
        "• Use 2-space indentation.\n"
        "• Quote strings containing special characters.\n"
        "• Add comments (# comment) to explain sections.\n"
    ),
    "toml": (
        "• Output ONLY valid TOML.\n"
        "• Group related keys under [sections].\n"
        "• Add comments for each section.\n"
        "• Use proper types (strings quoted, numbers unquoted, booleans true/false).\n"
    ),
}


def _file_type_hint(filename):
    if not filename:
        return "file"
    ext = os.path.splitext(filename)[1].lower()
    if ext in DATA_EXTS:
        return f"data file ({ext})"
    if ext in CODE_EXTS:
        lang = CODE_LANG.get(ext, ext.lstrip("."))
        return f"{lang} source code file ({ext})"
    if ext in DOC_EXTS:
        return f"document ({ext})"
    return f"file ({ext})"


def _rewrite_rules(filename):
    if not filename:
        return ""
    ext = os.path.splitext(filename)[1].lower()

    if ext in DATA_EXTS:
        return (
            "• This is a DATA file. NEVER delete rows unless explicitly asked.\n"
            "• NEVER fabricate rows not in the original.\n"
            "• Preserve all existing values unless the instruction targets them.\n"
            "• Keep the exact same format (CSV stays CSV, JSON stays JSON).\n"
        )
    if ext in CODE_EXTS:
        lang = CODE_LANG.get(ext, "code")
        rules = _LANG_RULES.get(lang, "")
        return (
            f"• This is a {lang.upper()} SOURCE FILE. "
            f"Preserve all logic not mentioned in the instruction.\n"
            "• NEVER remove functions, classes, or imports unless explicitly told to.\n"
            "• Keep indentation and code style consistent with the original.\n"
            f"• Output ONLY valid {lang} — no markdown, no explanations.\n"
            + (f"• Language conventions:\n{rules}" if rules else "")
        )
    if ext in (".html", ".htm"):
        return (
            "• This is an HTML file. Preserve all tags and structure not mentioned.\n"
            "• Keep DOCTYPE, head, and body intact unless instructed otherwise.\n"
            "• Output ONLY valid HTML.\n"
        )
    if ext in (".yaml", ".yml", ".toml", ".ini", ".cfg"):
        return (
            "• This is a CONFIG file. Preserve all keys/sections not mentioned.\n"
            "• NEVER remove config entries unless explicitly asked.\n"
            "• Keep the exact same format and indentation.\n"
        )
    return ""


def explain_prompt(filename, content):
    ftype = _file_type_hint(filename)
    ext   = os.path.splitext(filename)[1].lower() if filename else ""
    lang  = CODE_LANG.get(ext, "")

    code_hint = (
        f"- For code: describe what the {lang} code does, "
        f"its main functions/classes, inputs and outputs.\n"
        if lang else
        "- For code: describe main functions/classes and what they do.\n"
    )
    data_hint = (
        "- For data files: describe columns, row count, data types, and notable patterns.\n"
        if ext in DATA_EXTS else ""
    )

    return f"""You are a code and file analyst.

Explain the following {ftype} clearly and concisely.

RULES:
- Describe what the file does and its purpose.
{code_hint}{data_hint}- Keep the explanation under 200 words.
- Do NOT modify or reproduce the file content.
- Do NOT use markdown headers.

FILE: {filename}

CONTENT:
{content}

Provide your explanation now.
"""


def code_prompt(language, instructions, filename=None):
    """
    Generate code in any language.
    language: e.g. 'python', 'java', 'javascript', etc.
    """
    lang_lower = language.lower()
    rules      = _LANG_RULES.get(lang_lower, f"• Output ONLY valid {language} code.\n• No markdown. No explanations.\n")
    file_hint  = f"\nThe output will be saved as: {filename}\n" if filename else ""

    return f"""Generate {language} code.
{file_hint}
STRICT RULES:
{rules}• No markdown fences. No backticks. No explanations outside code.
• Output ONLY the raw code content — nothing else.

INSTRUCTIONS:
{instructions}

OUTPUT ONLY {language.upper()} CODE.
"""


def multi_file_prompt(instructions):
    return f"""Generate one or more files of any type.

STRICT FORMAT — repeat for each file:

FILE: path/to/file.ext
<file content here>

RULES:
• The very next line after FILE: must be file content. No blank lines between them.
• Do NOT add preamble, explanations, or markdown outside file blocks.
• Match the exact format and conventions for each file type:
  Python     (.py)  : 4-space indent, imports at top, if __name__=="__main__" block
  JavaScript (.js)  : ES6+, const/let, arrow functions, JSDoc comments
  TypeScript (.ts)  : explicit types, interfaces, ES6+
  Java       (.java): class matching filename, main() if runnable, Javadoc
  C#         (.cs)  : namespace + class, XML doc comments
  C/C++      (.c/.cpp): #include headers, main() if runnable
  Go         (.go)  : package + imports, main() in package main
  Ruby       (.rb)  : 2-space indent, snake_case
  PHP        (.php) : <?php tag, PSR-12 style
  SQL        (.sql) : uppercase keywords, semicolons, comments
  HTML       (.html): DOCTYPE, semantic tags
  CSS        (.css) : 2-space indent inside rules
  YAML       (.yaml): 2-space indent, quoted special chars
  JSON       (.json): valid JSON only
  XML        (.xml) : XML declaration, proper nesting
  Markdown   (.md)  : proper heading hierarchy
  CSV        (.csv) : header row + realistic data rows

REQUEST:
{instructions}
"""


def rewrite_prompt(content, instructions, row_count=None, filename=None):
    row_hint   = (
        f"\nThe original has {row_count} data rows. "
        f"Your output MUST contain at least that many rows "
        f"unless the user explicitly asked to remove rows.\n"
    ) if row_count else ""
    type_rules = _rewrite_rules(filename)

    return f"""You are editing an existing file. Apply ONLY the changes the user requested.

STRICT RULES:
1. PRESERVE all content not mentioned in the instruction.
2. NEVER fabricate new data, rows, or code not present in the original.
3. NEVER add explanations, commentary, or markdown fences.
4. NEVER truncate, summarize, or shorten the content.
5. ONLY change what the instruction specifically targets.
6. Output ONLY the complete modified file content — nothing else.
{row_hint}
FILE-TYPE SPECIFIC RULES:
{type_rules if type_rules else "• Maintain the original file format and style exactly."}

CURRENT FILE CONTENT:
{content}

MODIFICATION INSTRUCTION:
{instructions}

OUTPUT THE COMPLETE MODIFIED FILE CONTENT ONLY.
"""


def validation_prompt(content):
    return f"""You are a strict file content validator.

Check if the following content is ONLY valid file content with NO prose, explanations, or LLM filler.

Respond with EXACTLY one of:

VALID
or
INVALID: <one-line reason>

RULES — mark INVALID if ANY of these are true:
- Starts with natural language like "Here is", "Sure,", "Below is", "This code", "Certainly"
- Contains lines that are plain English explanations mixed into code or data
- Contains markdown fences (``` or ```) around the content
- Is empty or only whitespace
- For CSV/TSV: has no header row or no data rows
- For JSON: is not parseable as JSON
- For code: contains English prose sentences that are not comments
- For HTML: has no HTML tags at all

Mark VALID if:
- Content is purely code, data, markup, or config with no LLM filler
- Short files (even 1-2 lines) are VALID if they are proper file content
- Code comments (#, //, /*, --) are fine — they are not prose

CONTENT:
{content}
"""


def folder_analysis_prompt(file_contents, user_request):
    return f"""Analyze the following project files and answer the user's request.

{file_contents}

USER REQUEST:
{user_request}

Provide a clear analysis covering:
- Overall project structure and purpose
- What each file does (note the language/format for code files)
- How the files relate to each other
- Any observations relevant to the user's request

Be concise. Do not reproduce file contents verbatim.
"""
