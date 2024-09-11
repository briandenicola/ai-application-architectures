#pip install pyautogen
import os

from dotenv import load_dotenv
from pathlib import Path
from autogen import ConversableAgent

BASE_DIR = Path(__file__).absolute().parent

def chat() -> str:
    """Flow entry function."""

    if "OPENAI_API_KEY" not in os.environ and "AZURE_OPENAI_API_KEY" not in os.environ:
        # load environment variables from .env file
        load_dotenv()

    romulus = ConversableAgent(
        "romulus",
        system_message="Your name is Romulus and you are a twin with your brother Remus.  You are arguing over which of the seven hills your new city will be founded on. You are the wiser of the two.",
        llm_config={"config_list": [
            {
                "model": "gpt-35-turbo",
                "api_type": "azure",
                "api_key": os.environ['AZURE_OPENAI_API_KEY'],
                "azure_endpoint": os.environ['AZURE_OPENAI_ENDPOINT'],
                "api_version": "2024-05-01-preview" 
            }     
        ]},
        human_input_mode="NEVER",  # Never ask for human input.
    )

    remus = ConversableAgent(
        "remus",
        system_message="Your name is Remus and you are a twin with your brother Romulus.  You are arguing over which of the seven hills your new city will be founded on.  You are the older brother and more king like.",
        llm_config={"config_list": [
            {
                "model": "gpt-35-turbo",
                "api_type": "azure",
                "api_key": os.environ['AZURE_OPENAI_API_KEY'],
                "azure_endpoint": os.environ['AZURE_OPENAI_ENDPOINT'],
                "api_version": "2024-05-01-preview" 
            }     
        ]},
        human_input_mode="NEVER",  # Never ask for human input.
    )

    result = romulus.initiate_chat(remus, message="Remus, let's start a city one of these 7 hills - Aventine, Caelian, Capitoline, Esquiline, Palatine, Quirinal, Viminal. Which one should we found it on.", max_turns=4)


if __name__ == "__main__":
    result = chat()
    print(result)