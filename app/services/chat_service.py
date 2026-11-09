"""
ScholarAI Chat Service.

Coordinates the integrated Phase 17 chat workflow.
"""

import logging

from app.schemas.response_intelligence import (
    ResponseFormat,
    ResponseIntelligenceRequest,
)

from app.schemas.query_classification import (
    AcademicTaskType,
    QueryClassification,
)

from app.services.safety_service import (
    evaluate_message,
    validate_output,
)

from app.services.query_classification_service import (
    query_classification_service,
)

from app.services.query_rewriting_service import (
    query_rewriting_service,
)

from app.services.llm_providers.generation import (
    generate_with_provider_router,
)

from app.services.response_intelligence.response_intelligence_service import (
    response_intelligence_service,
)


logger = logging.getLogger(__name__)

# Backward-compatible alias for existing tests.
# Production generation continues through the provider router.
generate_llm_response = generate_with_provider_router


def _select_response_format(
    task_type: AcademicTaskType,
) -> ResponseFormat:

    format_mapping = {
        AcademicTaskType.COMPARISON: ResponseFormat.COMPARISON,
        AcademicTaskType.PROBLEM_SOLVING: ResponseFormat.STEP_BY_STEP,
        AcademicTaskType.SUMMARIZATION: ResponseFormat.SUMMARY,
    }

    return format_mapping.get(
        task_type,
        ResponseFormat.PLAIN_TEXT,
    )


async def generate_chat_response(
    message: str,
    *,
    llm_generator=None,
) -> str:

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message cannot be empty.")

    message = message.strip()

    # =====================================================
    # STEP 1: INPUT SAFETY
    # =====================================================

    safety_result = evaluate_message(message)

    if not safety_result.allowed:
        return (
            safety_result.response
            or "This request cannot be processed."
        )

    # =====================================================
    # STEP 2: QUERY CLASSIFICATION
    # =====================================================

    classification = query_classification_service.classify(
        query=message,
        has_conversation_context=False,
        has_document_context=False,
    )

    if isinstance(classification, QueryClassification):

        logger.info(
            "ScholarAI query classified",
            extra={
                "intent": classification.intent.value,
                "task_type": classification.task_type.value,
                "confidence": classification.confidence,
                "suggested_workflow": classification.suggested_workflow,
                "ambiguous": classification.ambiguous,
                "classifier_version": classification.classifier_version,
            },
        )

        # =================================================
        # STEP 3: QUERY REWRITING
        # =================================================

        rewrite_result = query_rewriting_service.rewrite(
            query=message,
            classification=classification,
        )

        logger.info(
            "ScholarAI query rewritten",
            extra={
                "strategy": rewrite_result.strategy.value,
                "rewritten": rewrite_result.rewritten,
                "context_used": rewrite_result.context_used,
                "classifier_version": rewrite_result.classifier_version,
            },
        )

        generation_prompt = rewrite_result.standalone_query
        task_type = classification.task_type

    else:
        # Fail safely without allowing an invalid classifier
        # result to break the chat workflow.
        logger.warning(
            "Invalid query classification received. "
            "Using the original query."
        )

        generation_prompt = message
        task_type = AcademicTaskType.GENERAL

    # =====================================================
    # STEP 4: LLM PROVIDER ROUTING
    # =====================================================

    generator = (
        llm_generator
        if llm_generator is not None
        else generate_llm_response
    )

    answer = await generator(generation_prompt)

    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError(
            "The LLM provider returned an invalid response."
        )

    answer = answer.strip()

    # =====================================================
    # STEP 5: OUTPUT SAFETY
    # =====================================================

    output_result = validate_output(answer)

    if not output_result.allowed:
        return (
            output_result.response
            or "The generated response could not be displayed."
        )

    # =====================================================
    # STEP 6: RESPONSE INTELLIGENCE
    # =====================================================

    response_format = _select_response_format(task_type)

    intelligence_result = response_intelligence_service.process(
        ResponseIntelligenceRequest(
            response=answer,
            response_format=response_format,
            validate_safety=False,
        )
    )

    logger.info(
        "ScholarAI response intelligence completed",
        extra={
            "response_format": (
                intelligence_result.response_format.value
            ),
            "validation_status": (
                intelligence_result.validation_status.value
            ),
            "quality_issue_count": len(
                intelligence_result.quality_issues
            ),
            "character_count": intelligence_result.character_count,
            "word_count": intelligence_result.word_count,
        },
    )

    return intelligence_result.response