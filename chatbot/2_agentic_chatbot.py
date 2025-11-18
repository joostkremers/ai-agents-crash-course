import chainlit as cl
import dotenv
from openai.types.responses import ResponseTextDeltaEvent

from agents import Runner
from nutrition_agent import nutrition_agent

dotenv.load_dotenv()

# What we want to do here is twofold:
#
# 1. Display the response one token at a time, instead of waiting until the
#    output is complete, so the user can see the bot is working. We need the
#    class `ResponsteTextDeltaEvent` for this, because makes it possible to detect
#    changes in the output text.
#
# 2. Show tool use in the UI.


@cl.on_message
async def on_message(message: cl.Message):

    # We use `Runner.run_streamed` here, because we want to be able to capture
    # the output word by word.
    result = Runner.run_streamed(
        nutrition_agent,
        message.content,
    )

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
