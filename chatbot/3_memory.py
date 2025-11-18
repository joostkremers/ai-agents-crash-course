import chainlit as cl
import dotenv
from openai.types.responses import ResponseTextDeltaEvent

from agents import Runner, SQLiteSession
from nutrition_agent import nutrition_agent

dotenv.load_dotenv()

# Here, we add memory to the chatbot. Chainlit provides sessions that can
# maintain state per session, i.e., browser window.


@cl.on_chat_start
async def on_chat_start():  # The function name is arbitraty.
    session = SQLiteSession("conversation_history")
    # IIUC `user_session` is essentially a key/value store that can store any
    # value you like. There are a few reserved keys (see the docs), but
    # otherwise you can add any key you like. Here, it is used to store an
    # `SQLiteSession` instance, which might look funny because the
    # `user_session` is already a session store, but we need it because we want
    # to pass it to `Runner.run_streamed` below.
    cl.user_session.set("agent_session", session)


@cl.on_message
async def on_message(message: cl.Message):

    session = cl.user_session.get("agent_session")

    # We use `Runner.run_streamed` here, because we want to be able to capture
    # the output word by word.
    result = Runner.run_streamed(nutrition_agent, message.content, session=session)

    # To stream the response, first create an empty message:
    msg = cl.Message(content="")

    # The iterate over the result stream and process each event:
    async for event in result.stream_events():
        # Check if we have a text delta event:
        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            # We stream the token to the UI and also output it to the console.
            await msg.stream_token(token=event.data.delta)
            print(event.data.delta, end="", flush=True)

        elif (
            # Alternatively, check if we have a tool call event:
            event.type == "raw_response_event"
            and hasattr(event.data, "item")
            and hasattr(event.data.item, "type")
            and event.data.item.type == "function_call"
            and len(event.data.item.arguments) > 0
        ):
            # The `cl.Step` class creates a step in the chatbot UI. It has an
            # input and an output, which can both be displayed. Here, we only
            # display the input, which is hidden by default.
            with cl.Step(name=f"{event.data.item.name}", type="tool") as step:
                step.input = event.data.item.arguments
                print(
                    f"\nTool call: {
                        event.data.item.name} with args: {
                        event.data.item.arguments}"
                )

    await msg.update()
