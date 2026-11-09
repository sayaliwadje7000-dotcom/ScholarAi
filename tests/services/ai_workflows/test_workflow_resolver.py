import pytest

from app.services.ai_workflows.exceptions import (
    WorkflowReferenceResolutionError,
)

from app.services.ai_workflows.workflow_resolver import (
    WorkflowReferenceResolver,
)


@pytest.fixture
def resolver():

    return WorkflowReferenceResolver()


@pytest.fixture
def inputs():

    return {
        "query": "binary search",
        "subject": "Data Structures",
    }


@pytest.fixture
def step_outputs():

    return {
        "resource_search": {
            "query": "binary search",
            "count": 5,
        }
    }


def test_resolves_workflow_input(
    resolver,
    inputs,
    step_outputs,
):

    result = resolver.resolve_reference(
        "input.query",
        inputs,
        step_outputs,
    )

    assert result == "binary search"


def test_resolves_previous_step_output(
    resolver,
    inputs,
    step_outputs,
):

    result = resolver.resolve_reference(
        "steps.resource_search.output.count",
        inputs,
        step_outputs,
    )

    assert result == 5


def test_resolves_nested_template(
    resolver,
    inputs,
    step_outputs,
):

    template = {
        "query": {
            "$ref": "input.query"
        },
        "metadata": {
            "subject": {
                "$ref": "input.subject"
            }
        },
    }

    result = resolver.resolve_template(
        template,
        inputs,
        step_outputs,
    )

    assert result == {
        "query": "binary search",
        "metadata": {
            "subject": "Data Structures"
        },
    }


def test_rejects_missing_input_reference(
    resolver,
    inputs,
    step_outputs,
):

    with pytest.raises(WorkflowReferenceResolutionError):

        resolver.resolve_reference(
            "input.missing",
            inputs,
            step_outputs,
        )


def test_rejects_missing_step_output(
    resolver,
    inputs,
    step_outputs,
):

    with pytest.raises(WorkflowReferenceResolutionError):

        resolver.resolve_reference(
            "steps.missing.output.result",
            inputs,
            step_outputs,
        )


def test_rejects_unsupported_namespace(
    resolver,
    inputs,
    step_outputs,
):

    with pytest.raises(WorkflowReferenceResolutionError):

        resolver.resolve_reference(
            "python.os.system",
            inputs,
            step_outputs,
        )


def test_preserves_literal_strings(
    resolver,
    inputs,
    step_outputs,
):

    result = resolver.resolve_template(
        {
            "query": "binary search"
        },
        inputs,
        step_outputs,
    )

    assert result == {
        "query": "binary search"
    }