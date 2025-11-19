import os
import chainlit as cl
import dotenv
from openai.types.responses import ResponseTextDeltaEvent

from agents import InputGuardrailTripwireTriggered, Runner, SQLiteSession
from nutrition_agent import NutritionAgent

dotenv.load_dotenv()


@cl.on_chat_start
async def on_chat_start():  # The function name is arbitraty.
    session = SQLiteSession("conversation_history")
    agent = NutritionAgent()
    cl.user_session.set("agent_session", session)
    cl.user_session.set("agent", agent.breakfast_advisor)
    await agent.exa_search_mcp.connect()


@cl.on_message
async def on_message(message: cl.Message):

    session = cl.user_session.get("agent_session")
    agent = cl.user_session.get("agent")

    try:
        result = Runner.run_streamed(agent, message.content, session=session)

        # To stream the response, first create an empty message:
        msg = cl.Message(content="")

        # Then iterate over the result stream and process each event:
        async for event in result.stream_events():
            # Check if we have a text delta event:
            if event.type == "raw_response_event" and isinstance(
                event.data, ResponseTextDeltaEvent
            ):
                await msg.stream_token(token=event.data.delta)

            elif (
                # Alternatively, check if we have a tool call event:
                event.type == "raw_response_event"
                and hasattr(event.data, "item")
                and hasattr(event.data.item, "type")
                and event.data.item.type == "function_call"
                and len(event.data.item.arguments) > 0
            ):
                with cl.Step(name=f"{event.data.item.name}", type="tool") as step:
                    step.input = event.data.item.arguments

        await msg.update()

    except InputGuardrailTripwireTriggered as e:
        await cl.Message("Sorry, I cannot help you with that.").send()


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    if (username, password) == (
        os.getenv("CHAINLIT_USERNAME"),
        os.getenv("CHAINLIT_PASSWORD"),
    ):
        return cl.User(identifier="VJ&em", metadata={"role": "bossman"})
    else:
        return None
