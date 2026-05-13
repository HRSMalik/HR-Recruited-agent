from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt
from langgraph.checkpoint.memory import InMemorySaver
from typing import TypedDict, Optional, List
import os
from dotenv import load_dotenv
load_dotenv()


memory = InMemorySaver()

class JobPostState(TypedDict):
    form_data: dict
    generated_post: Optional[str]
    human_feedback: Optional[str]
    approved: bool



def review_router(state):

    action = state["human_feedback"]["action"]

    if action == "approve":
        return "approved"

    elif action == "edit":
        return "format"

    elif action == "regenerate":
        return "regenerate"
    

def generate_post_node(state):

    data = state["form_data"]

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
    llm = init_chat_model("gpt-4o", temperature=3.0, max_tokens=300)
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


def create_workflow_agent():
    workflow = StateGraph(JobPostState)

    workflow.add_node("generate_job_post", generate_post_node)
    workflow.add_node("human_review", human_review)
    workflow.add_node("regenerate_post", regenerate_node)
    workflow.add_node("format_post", format_node)

    workflow.set_entry_point("generate_job_post")

    workflow.add_edge("generate_job_post", "human_review")
    workflow.add_conditional_edges(
        "human_review",
        review_router,
        {
            "approved": "format_post",
            "format": "format_post",
            "regenerate": "regenerate_post"
        }
    )
    workflow.add_edge("regenerate_post", "human_review")
    workflow.add_edge("format_post", END)

    graph = workflow.compile(checkpointer=memory)
    return graph



if __name__ == "__main__":
    import uuid
    thread_id = str(uuid.uuid4())
    config = {
            "configurable": {"thread_id": thread_id}
            }
    
    agent = create_workflow_agent()
    response = agent.invoke({
    "form_data": {
        "title": "Software Engineer",
        "experience_level": "Mid-level",
        "description": "We are looking for a skilled software engineer MERN Stack to join our team.",
        "requirements": "3+ years of experience in software development, proficiency in React, TypeScript and JavaScript."
    }
    }, config=config)
   

    
    # try:
    #     print(agent.get_graph().draw_mermaid())
    # except Exception as e:
    #     print(f"Graph visualization not available: {e}")
