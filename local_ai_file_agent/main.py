"""
main.py — entry point for the File Agent CLI.

Configuration is read from agent.config.yaml in this directory.
Edit that file to change the model, URL, timeouts, and paths.

─────────────────────────────────────────────────────────────────
HOW OUTPUT WORKS
─────────────────────────────────────────────────────────────────
All agent output flows through agent.bus.bus (an AgentBus instance).
By default it prints everything to the console — identical to before.

To intercept output in a master agent, replace the handler BEFORE
calling start_agent():

    from agent.bus import bus

    # Collect all events as structured dicts
    events = []
    def my_handler(event):
        # event = {level, text, end, timestamp}
        print(event["text"], end=event["end"])   # still print to console
        events.append(event)                     # AND collect for master

    bus.set_handler(my_handler)
    start_agent()

Event levels:
  "output"  — general agent output (results, file contents, etc.)
  "info"    — progress/status messages (classifying, scanning, etc.)
  "success" — operation completed successfully (✅ lines)
  "warning" — something unexpected but agent continued (⚠ lines)
  "error"   — operation failed (❌ lines)
  "prompt"  — the agent is about to ask the user something

─────────────────────────────────────────────────────────────────
"""

from agent.bus import bus
from cli.agent_loop import start_agent

# Default: print everything to console (no change from previous behaviour)
# To customise, call bus.set_handler(your_fn) here before start_agent().

if __name__ == "__main__":
    start_agent()
