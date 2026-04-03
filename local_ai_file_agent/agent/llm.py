"""
llm.py — LLM client with timeout, retry-with-backoff, and streaming progress.
Reads all settings from config.py (which reads agent.config.yaml).
"""

import time
import requests
from .config import (
    LLM_URL, LLM_MODEL, LLM_TIMEOUT,
    LLM_RETRY_ATTEMPTS, LLM_RETRY_DELAY, LLM_PROVIDER
)

# Runtime override — set_model() in main.py or agent_api.py can override config
_override = {}


def set_model(cfg):
    """Legacy entry point — main.py calls this. Updates runtime config."""
    global _override
    _override = cfg


def _get_cfg():
    """Return effective config (override takes precedence over yaml config)."""
    return {
        "url":     _override.get("url",   LLM_URL),
        "model":   _override.get("model", LLM_MODEL),
        "timeout": _override.get("timeout_seconds", LLM_TIMEOUT),
    }


def call_llm(prompt, show_progress=False):
    """
    Call the LLM with automatic retry and timeout.

    Args:
        prompt:        The prompt string.
        show_progress: If True, print a spinner while waiting.

    Returns:
        Response text string, or empty string on failure.
    """
    cfg      = _get_cfg()
    url      = cfg["url"]
    model    = cfg["model"]
    timeout  = cfg["timeout"]
    attempts = LLM_RETRY_ATTEMPTS
    delay    = LLM_RETRY_DELAY

    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            if show_progress and attempt == 1:
                print("  ⏳ Waiting for model response...", end="\r", flush=True)

            resp = requests.post(
                url,
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=timeout,
            )
            resp.raise_for_status()

            if show_progress:
                print(" " * 45, end="\r")  # clear the spinner line

            return resp.json().get("response", "")

        except requests.exceptions.Timeout:
            last_error = f"LLM timed out after {timeout}s"
        except requests.exceptions.ConnectionError:
            last_error = f"Cannot connect to LLM at {url}"
        except requests.exceptions.HTTPError as e:
            last_error = f"LLM HTTP error: {e}"
        except Exception as e:
            last_error = f"LLM error: {e}"

        if attempt < attempts:
            print(f"  ⚠  {last_error} — retrying in {delay}s (attempt {attempt}/{attempts})")
            time.sleep(delay)
            delay *= 1.5   # exponential backoff

    print(f"  ❌ LLM failed after {attempts} attempts: {last_error}")
    return ""
