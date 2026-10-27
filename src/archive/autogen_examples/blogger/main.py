import os
from datetime import datetime
from typing import Callable, Dict, Literal, Optional, Union

from typing_extensions import Annotated

from autogen import (
    Agent,
    AssistantAgent,
    ConversableAgent,
    GroupChat,
    GroupChatManager,
    UserProxyAgent,
    config_list_from_json,
    register_function,
)
from autogen.agentchat.contrib import agent_builder
from autogen.cache import Cache
from autogen.coding import DockerCommandLineCodeExecutor, LocalCommandLineCodeExecutor

config_list = [
    {
        "model": "gpt-4o",
        "api_type": "azure",
        "api_key": os.environ['AZURE_OPENAI_API_KEY'],
        "azure_endpoint": os.environ['AZURE_OPENAI_ENDPOINT'],
        "api_version": "2025-01-01-preview" 
    }  
    #},
    # {
    #     "model": "gpt-35-turbo",
    #     "api_type": "azure",
    #     "api_key": os.environ['AZURE_OPENAI_API_KEY'],
    #     "azure_endpoint": os.environ['AZURE_OPENAI_ENDPOINT'],
    #     "api_version": "2024-05-01-preview" 
    # }
]

user_proxy = UserProxyAgent(
    name="Admin",
    system_message="A human admin. Give the task, and send instructions to writer to refine the blog post.",
    code_execution_config=False,
)

planner = AssistantAgent(
    name="Planner",
    system_message="""Planner. Given a task, please determine what information is needed to complete the task.
Please note that the information will all be retrieved using Python code. Please only suggest information that can be retrieved using Python code.
""",
    llm_config={"config_list": config_list, "cache_seed": None},
)

engineer = AssistantAgent(
    name="Engineer",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""Engineer. You write python/bash to retrieve relevant information. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
""",
)

writer = AssistantAgent(
    name="Writer",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""Writer. Please write blogs in markdown format (with relevant titles) and put the content in pseudo ```md``` code block. You will write it for a task based on previous chat history. Don't write any code.""",
)

os.makedirs("paper", exist_ok=True)
code_executor = UserProxyAgent(
    name="Executor",
    system_message="Executor. Execute the code written by the engineer and report the result.",
    description="Executor should always be called after the engineer has written code to be executed.",
    human_input_mode="ALWAYS",
    code_execution_config={
        "last_n_messages": 3,
        "executor": LocalCommandLineCodeExecutor(work_dir="paper"),
    },
)

groupchat = GroupChat(
    agents=[user_proxy, engineer, code_executor, writer, planner],
    messages=[],
    max_round=20,
    speaker_selection_method="auto",
)
manager = GroupChatManager(groupchat=groupchat, llm_config={"config_list": config_list, "cache_seed": None})

task = (
    f"Today is {datetime.now().date()}. Write a blogpost about the stock price performance of Nvidia in the past month."
)

with Cache.disk(cache_seed=41) as cache:
    chat_history = user_proxy.initiate_chat(
        manager,
        message=task,
        cache=cache,
    )