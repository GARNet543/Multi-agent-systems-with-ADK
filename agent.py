import os
import logging
import google.cloud.logging

from callback_logging import log_query_to_model, log_model_response
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.agents import SequentialAgent, LoopAgent, ParallelAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.langchain_tool import LangchainTool  # import
from google.adk.tools import exit_loop
from google.adk.models import Gemini
from google.genai import types

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper


cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv()

model_name = os.getenv("MODEL")
print(model_name)

RETRY_OPTIONS = types.HttpRetryOptions(initial_delay=1, attempts=6)

# Tools


def append_to_state(
    tool_context: ToolContext, field: str, response: str
) -> dict[str, str]:
    """Append new output to an existing state key.

    Args:
        field (str): a field name to append to
        response (str): a string to append to the field

    Returns:
        dict[str, str]: {"status": "success"}
    """
    existing_state = tool_context.state.get(field, [])
    tool_context.state[field] = existing_state + [response]
    logging.info(f"[Added to {field}] {response}")
    return {"status": "success"}


def write_file(
    tool_context: ToolContext,
    directory: str,
    filename: str,
    content: str
) -> dict[str, str]:
    target_path = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w") as f:
        f.write(content)
    return {"status": "success"}


# Agents
# --- Improved Agents ---

The_Critic = Agent(
    name="The_Critic",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Researches controversies and negative aspects.",
    instruction="""
    1. Check {CRITICAL_FEEDBACK?} for specific guidance from the Judge on what was missing in previous rounds.
    2. Research the historical figure in {PROMPT} focusing on controversies and negative impacts.
    3. Use the wikipedia tool to search for '{PROMPT} controversy' or specific gaps mentioned in feedback.
    4. Append your detailed findings to the 'NEGATIVE_ARGUMENTS' state key.
    5. Summarize your current stance for the prosecution.
    """,
    tools=[
        LangchainTool(tool=WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())),
        append_to_state,
    ],
)

The_Admirer = Agent(
    name="The_Admirer",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Researches accomplishments and positive aspects.",
    instruction="""
    1. Check {CRITICAL_FEEDBACK?} for specific guidance from the Judge.
    2. Research the historical figure in {PROMPT} focusing on accomplishments and positive contributions.
    3. Use the wikipedia tool to search for '{PROMPT} achievements' or topics requested in feedback.
    4. Append your detailed findings to the 'POSITIVE_ARGUMENTS' state key.
    5. Summarize your current stance for the defense.
    """,
    tools=[
        LangchainTool(tool=WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())),
        append_to_state,
    ],
)

The_Investigation = ParallelAgent(
    name="The_Investigation",
    description="Gathers balanced arguments in parallel.",
    sub_agents=[The_Critic, The_Admirer]
)

judge = Agent(
    name="judge",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="The quality gatekeeper of the moot court.",
    instruction="""
    CONTEXT:
    - Prosecution: {NEGATIVE_ARGUMENTS?}
    - Defense: {POSITIVE_ARGUMENTS?}

    EVALUATION STEPS:
    1. Compare the depth of both arguments. 
    2. If the data is one-sided or too brief, use 'append_to_state' to add specific instructions to 'CRITICAL_FEEDBACK'. Do NOT exit yet.
    3. If the data is comprehensive and balanced, synthesize it into a formal "Final Verdict" report.
    4. Append the final report to 'FINAL_REPORT' and call 'exit_loop'.
    """,
    tools=[append_to_state, exit_loop],
)

# --- Updated Inquiry Logic ---

The_Trial_And_Review = LoopAgent(
    name="The_Trial_And_Review",
    description="Iterative court proceedings.",
    sub_agents=[The_Investigation, judge],
    max_iterations=3,
)

Verdict = Agent(
    name="Verdict",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Saves the report to disk.",
    instruction="""
    - Retrieve the 'FINAL_REPORT' (which is a list of strings). 
    - Combine the report parts into a single document.
    - Save to 'moot_court_reports' as '{PROMPT}.txt' using 'write_file'.
    """,
    tools=[write_file],
)

The_Inquiry = SequentialAgent(
    name="The_Inquiry",
    description="Full analysis pipeline.",
    sub_agents=[The_Trial_And_Review, Verdict],
)

root_agent = Agent(
    name="root",
    model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
    description="Primary interface for the Moot Court.",
    instruction="""
    - Introduce yourself as the Moot Court Coordinator.
    - Ask the user which historical figure they would like to investigate.
    - Once the user provides a name, use 'append_to_state' to save it to the 'PROMPT' key.
    - After saving, transfer control to 'The_Inquiry'.
    """,
    tools=[append_to_state],
    sub_agents=[The_Inquiry],
    generate_content_config=types.GenerateContentConfig(temperature=0),
)