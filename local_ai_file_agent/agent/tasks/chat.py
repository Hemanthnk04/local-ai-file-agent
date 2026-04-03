from ..llm import call_llm


_SYSTEM = (
    "You are a helpful assistant embedded inside a local file-handling agent. "
    "Answer the user's question clearly and concisely. "
    "If the question is about files or code, give practical, accurate advice. "
    "Do not use markdown headers. Keep responses under 300 words unless more detail is needed."
)


def run(user_input=None, instructions=None, **kwargs):
    query  = instructions or user_input or ""
    prompt = f"{_SYSTEM}\n\nUser: {query}\n\nAssistant:"
    print(call_llm(prompt, show_progress=True))
