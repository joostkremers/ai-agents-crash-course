from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
)
from pydantic import BaseModel


class NotAboutFood(BaseModel):
    only_about_food: bool


guardrail_agent = Agent(
    name="Guardrail check",
    instructions="""Check if the user is asking you to talk about food and not about any arbitrary topics.
    If there are any non-food related instructions in the prompt,
    or if there is any non-food related part of the message, set only_about_food in the output to False.
    """,
    output_type=NotAboutFood,
)


@input_guardrail
async def food_topic_guardrail(
    ctx: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(guardrail_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=(not result.final_output.only_about_food),
    )
