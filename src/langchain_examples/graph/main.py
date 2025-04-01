#pip install langgraph
#pip install langchain_openai
import os
import openai

from dotenv import load_dotenv
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from langchain_openai import AzureChatOpenAI

# Graph state
class State(TypedDict):
    topic: str
    joke: str
    improved_joke: str
    final_joke: str

if "AZURE_OPENAI_ENDPOINT" not in os.environ and "AZURE_OPENAI_API_KEY" not in os.environ:
    load_dotenv("../../.env")

llm = AzureChatOpenAI(
    azure_deployment = "gpt-4o",
    api_version     = "2025-01-01-preview",
    temperature     = 0.7,
    max_tokens      = 200
)

def generate_joke(state: State):
    """First LLM call to generate initial joke"""
    msg = llm.invoke(f"Write a short joke about {state['topic']}")
    return {"joke": msg.content}

def check_punchline(state: State):
    """Gate function to check if the joke has a punchline"""
    if "?" in state["joke"] or "!" in state["joke"]:
        return "Fail"
    return "Pass"

def improve_joke(state: State):
    """Second LLM call to improve the joke"""
    msg = llm.invoke(f"Make this joke funnier by adding wordplay: {state['joke']}")
    return {"improved_joke": msg.content}

def polish_joke(state: State):
    """Third LLM call for final polish"""
    msg = llm.invoke(f"Add a surprising twist to this joke: {state['improved_joke']}")
    return {"final_joke": msg.content}
    
def workflow(topic: str) -> object:
    """Workflow entry function."""

    workflow = StateGraph(State)
    workflow.add_node("generate_joke", generate_joke)
    workflow.add_node("improve_joke", improve_joke)
    workflow.add_node("polish_joke", polish_joke)

    workflow.add_edge(START, "generate_joke")
    workflow.add_conditional_edges(
        "generate_joke", check_punchline, {"Fail": "improve_joke", "Pass": END}
    )
    workflow.add_edge("improve_joke", "polish_joke")
    workflow.add_edge("polish_joke", END)
    
    chain = workflow.compile()
    #display(Image(chain.get_graph().draw_mermaid_png()))
    state = chain.invoke({"topic": topic})
    
    return(state)


if __name__ == "__main__":
    result = workflow("Ancient Rome")
    
    print("Initial joke:")
    print(result["joke"])
    print("\n--- --- ---\n")
    if "improved_joke" in result:
        print("Improved joke:")
        print(result["improved_joke"])
        print("\n--- --- ---\n")

        print("Final joke:")
        print(result["final_joke"])
    else:
        print("Joke failed quality gate - no punchline detected!")
    
   
