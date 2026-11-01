"""
ScholarAI Chat Service.

Coordinates:
1. Input validation.
2. Safety screening.
3. LLM response generation.
4. Output security validation.
"""

from app.services.llm_service import generate_llm_response

from app.services.safety_service import (
    evaluate_message,
    validate_output,
)


async def generate_chat_response(message: str) -> str:

    """
    Generate a safe academic response.

    The request is screened before reaching the LLM.
    The generated answer is checked before returning it.
    """

    # -----------------------------------------------------
    # STEP 1: INPUT SAFETY
    # -----------------------------------------------------

    safety_result = evaluate_message(message)

    if not safety_result.allowed:

        return safety_result.response

    # -----------------------------------------------------
    # STEP 2: GENERATE ACADEMIC RESPONSE
    # -----------------------------------------------------

    answer = await generate_llm_response(message)

    # -----------------------------------------------------
    # STEP 3: OUTPUT SECURITY
    # -----------------------------------------------------

    output_result = validate_output(answer)

    if not output_result.allowed:

        return output_result.response

    return answer