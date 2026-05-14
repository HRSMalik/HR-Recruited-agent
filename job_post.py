from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt
from langgraph.errors import GraphInterrupt
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict, Optional, List, Dict, Any
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import asyncio
import concurrent.futures
import sys
import os
from dotenv import load_dotenv
load_dotenv()



def _run_coro_sync(coro):
    """Run an async coroutine from sync code.

    If we're already inside an event loop, run it in a fresh thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro)).result()


_MCP_TOOL_SPECS_CACHE: Optional[list[dict[str, Any]]] = None


def _get_mcp_server_parameters() -> StdioServerParameters:
    """Spawn the local MCP server over stdio (mcp_server.py)."""
    server_script = os.path.join(os.path.dirname(__file__), "mcp_server.py")
    return StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        cwd=os.path.dirname(server_script) or os.getcwd(),
    )


async def _mcp_list_tools_async() -> list[dict[str, Any]]:
    params = _get_mcp_server_parameters()
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            res = await session.list_tools()
            specs: list[dict[str, Any]] = []
            for t in res.tools:
                specs.append(
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "inputSchema": (t.inputSchema or {}),
                    }
                )
            return specs


async def _mcp_call_tool_async(tool_name: str, arguments: dict[str, Any]) -> Any:
    params = _get_mcp_server_parameters()
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments=arguments)



memory = InMemorySaver()

class JobPostState(TypedDict):
    form_data: dict
    generated_post: Optional[str]
    human_feedback: Optional[Dict[str, Any]]
    approved: bool
    linkedin_posted: bool



def generate_post_node(state):

    data = state.get("form_data") if isinstance(state, dict) else None
    if not data:
        raise ValueError("Missing 'form_data' in workflow state. Start a new thread via /job-posts before calling /job-posts/{thread_id}/review.")

    prompt = f"""
    Create a professional job post for TekHqs Company.

    Requirements:
    {data}

    here is a sample post for reference:

    Senior Blockchain Pre-Sales (1 Position)

    Job Summary:
    Acts as a technical consultant in pre-sales engagements, designing blockchain solutions aligned with client requirements.

    Key Responsibilities:
    Engage with clients to understand technical needs
    Design blockchain-based solutions
    Support sales with demos and POCs
    Prepare technical proposals

    Requirements:

    5–8 years total experience in software development
    3–4+ years specifically in blockchain (hands-on with Solidity/Web3)
    Strong blockchain expertise (Solidity, Web3)
    Excellent communication and client-facing skills

    Good fit if you:
    Enjoy talking to people, not just coding
    Like designing systems
    Want influence over big technical decisions
    """
    llm = init_chat_model("gpt-4o", temperature=0.3)
    result = llm.invoke(prompt)

    return {
        **state,
        "generated_post": result.content
    }

def regenerate_node(state):

    feedback = state["human_feedback"]["feedback"]

    prompt = f"""
    Rewrite the job post.

    Previous version:
    {state['generated_post']}

    Feedback:
    {feedback}
    """
    llm = init_chat_model("gpt-4o", temperature=0.3, max_tokens=300)
    response = llm.invoke(prompt)

    return {
        **state,
        "generated_post": response.content
    }

def format_node(state):

    if state["human_feedback"]["action"] == "edit":

        final_post = state["human_feedback"]["edited_post"]

    else:
        final_post = state["generated_post"]

    return {
        **state,
        "approved": True,
        "generated_post": final_post
    }

def human_review(state):

    feedback = interrupt({
        "generated_post": state["generated_post"],
        "message":
            "Review the generated job post. "
            "Approve, edit, or request regeneration."
    })

    return {
        **state,
        "human_feedback": feedback
    }


def review_router(state):

    action = state["human_feedback"]["action"]

    if action == "approve":
        return "approved"

    elif action == "edit":
        return "format"

    elif action == "regenerate":
        return "regenerate"
    

def post_to_linkedin_node(state: dict) -> dict:
    content = state.get("generated_post")
    if not content or not str(content).strip():
        raise ValueError("Missing 'generated_post' in workflow state; nothing to post.")

    # Mark as approved when the human explicitly approved (approve path bypasses format_node).
    approved = bool(state.get("approved"))
    state = {**state, "approved": approved or True}

    _run_coro_sync(
        _mcp_call_tool_async(
            "post_to_linkedin",
            {
                "content": str(content),
                "headless": False,
            },
        )
    )

    return {**state, "linkedin_posted": True}

def create_workflow_agent():
    workflow = StateGraph(JobPostState)

    workflow.add_node("generate_job_post", generate_post_node)
    workflow.add_node("human_review", human_review)
    workflow.add_node("regenerate_post", regenerate_node)
    workflow.add_node("format_post", format_node)
    workflow.add_node("post_to_linkedin", post_to_linkedin_node)

    workflow.set_entry_point("generate_job_post")

    workflow.add_edge("generate_job_post", "human_review")
    workflow.add_conditional_edges(
        "human_review",
        review_router,
        {
            "approved": "post_to_linkedin",
            "format": "format_post",
            "regenerate": "regenerate_post"
        }
    )
    workflow.add_edge("regenerate_post", "human_review")
    workflow.add_edge("format_post", "post_to_linkedin")
    workflow.add_edge("post_to_linkedin", END)

    graph = workflow.compile(checkpointer=memory)
    return graph



if __name__ == "__main__":
    import uuid
    import sys

    def _read_multiline(prompt: str) -> str:
        print(prompt)
        print("(Finish by typing a single line with END)")
        lines: List[str] = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        return "\n".join(lines).strip()

    def _prompt_human_feedback(interrupt_value: Any) -> Dict[str, Any] | None:
        if not isinstance(interrupt_value, dict):
            interrupt_value = {}

        message = interrupt_value.get("message")
        generated_post = interrupt_value.get("generated_post")

        if message:
            print(f"\n{message}\n")
        if generated_post:
            print("--- Generated Job Post (Draft) ---")
            print(generated_post)
            print("--- End Draft ---\n")

        while True:
            action = input("Action? [a]pprove / [e]dit / [r]egenerate / [q]uit: ").strip().lower()
            if action in {"a", "approve"}:
                return {"action": "approve"}
            if action in {"e", "edit"}:
                edited = _read_multiline("Paste the fully edited job post:")
                return {"action": "edit", "edited_post": edited}
            if action in {"r", "regen", "regenerate"}:
                feedback = input("What should be changed (short feedback)? ").strip()
                return {"action": "regenerate", "feedback": feedback}
            if action in {"q", "quit", "exit"}:
                return None
            print("Invalid choice. Please enter a/e/r/q.")

    thread_id = str(uuid.uuid4())
    config = {
            "configurable": {"thread_id": thread_id}
            }
    
    agent = create_workflow_agent()

    initial_input = {
        "form_data": {
            "title": "Software Engineer",
            "experience_level": "Mid-level",
            "description": "We are looking for a skilled software engineer MERN Stack to join our team.",
            "requirements": "3+ years of experience in software development, proficiency in React, TypeScript and JavaScript.",
        }
    }

    pending = initial_input

    while True:

        response = agent.invoke(
            pending,
            config=config
        )

        # INTERRUPT DETECTED
        if "__interrupt__" in response:

            interrupts = response["__interrupt__"]

            interrupt_value = interrupts[0].value

            human_feedback = _prompt_human_feedback(
                interrupt_value
            )

            if human_feedback is None:
                print("Aborted by user.")
                sys.exit(1)

            pending = Command(
                resume=human_feedback
            )

            continue

        # WORKFLOW FINISHED
        break


    print("\nFINAL JOB POST:\n")
    print(response["generated_post"])
    # try:
    #     print(agent.get_graph().draw_mermaid())
    # except Exception as e:
    #     print(f"Graph visualization not available: {e}")
