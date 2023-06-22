import logging
from typing import Dict, List

from langchain.chains.base import Chain

from ix.chains.json import parse_json
from ix.chains.tests.test_config_loader import OPENAI_LLM
from ix.chat.models import Chat
from ix.task_log.models import TaskLogMessage
from ix.task_log.tasks.agent_runner import start_agent_loop

logger = logging.getLogger(__name__)


MODERATOR_PROMPT = """
You are a chat moderator. You direct messages to the agent who can best response to the user request

AGENTS:
{agents}

AGENT_FORMAT:
###START###
{{"agent": "agent_name"}}
###END###

QUESTION_FORMAT:
###START###
{{"question": "question text"}}
###END###

INSTRUCTION:
- Choose the agent from AGENTS who will process the user request.
- Respond in AGENT_FORMAT if returning an AGENT.
- If no AGENT can process the request, respond with QUESTION_FORMAT for a clarifying QUESTION.
- DO NOT ADD EXTRA FIELDS TO THE EXPECTED FORMAT
"""


LLM_CHOOSE_AGENT_CONFIG = {
    "class_path": "ix.chains.llm_chain.LLMChain",
    "config": {
        "llm": OPENAI_LLM,
        "prompt": {
            "class_path": "langchain.prompts.chat.ChatPromptTemplate",
            "config": {
                "messages": [
                    {
                        "role": "assistant",
                        "template": MODERATOR_PROMPT,
                        "input_variables": ["agents"],
                    },
                    {
                        "role": "user",
                        "template": "{user_input}",
                        "input_variables": ["user_input"],
                    },
                ]
            },
        },
    },
}


class ChatModerator(Chain):
    """
    Chain that compares user input to a list of agents and chooses the best agent to handle the task
    """

    selection_chain: Chain

    @property
    def _chain_type(self) -> str:
        return "ix_chat_moderator"

    @property
    def output_keys(self) -> List[str]:
        """Outputs task_id of spawned subtask"""
        return ["task_id"]

    @property
    def input_keys(self) -> List[str]:
        """Input keys this chain expects."""
        return ["user_input", "chat_id"]

    def agent_prompt(self, chat: Chat) -> str:
        """build prompt for configured tools"""
        lines = []
        for i, agent in enumerate(chat.agents.all()):
            lines.append(f"{i}. {agent.alias}: {agent.purpose}")
        return "\n".join(lines)

    def _call(self, inputs: Dict[str, str]) -> Dict[str, str]:
        # 1. select agent
        user_input = inputs["user_input"]
        chat_id = inputs["chat_id"]
        chat = Chat.objects.get(id=chat_id)
        logger.debug(f"Routing user_input={user_input}")
        response = self.selection_chain.run(
            user_input=user_input, agents=self.agent_prompt(chat)
        )
        logger.debug(f"Moderator returned response={response}")
        response_data = parse_json(response, output_key="agent")
        # TODO parse_json maps the whole return string to the agent key
        alias = response_data["agent"]["agent"]

        # 2. report delegation
        TaskLogMessage.objects.create(
            task_id=self.callbacks.task.id,
            role="assistant",
            parent=self.callbacks.think_msg,
            content={
                "type": "ASSISTANT",
                "text": f"Delegating to @{alias}",
                "agent": self.callbacks.task.agent.alias,
            },
        )

        # 3. delegate to the agent
        agent = chat.agents.get(alias=alias)
        subtask = chat.task.delegate_to_agent(agent)
        logger.debug(
            f"Delegated to agent={agent.alias} task={subtask.id} input={inputs}"
        )
        start_agent_loop.delay(
            task_id=str(subtask.id), chain_id=str(agent.chain_id), inputs=inputs
        )
        return {"task_id": str(subtask.id)}

    async def _acall(self, inputs: Dict[str, str]) -> Dict[str, str]:
        pass
