from typing import Any

from app.services.ai_workflows.exceptions import (
    WorkflowReferenceResolutionError,
)


class WorkflowReferenceResolver:

    @staticmethod
    def _read_path(
        source: Any,
        path: list[str],
    ) -> Any:

        current = source

        for part in path:

            if isinstance(current, dict):

                if part not in current:

                    raise WorkflowReferenceResolutionError(
                        f"Reference field '{part}' does not exist."
                    )

                current = current[part]

            else:

                raise WorkflowReferenceResolutionError(
                    "Workflow references can only access "
                    "structured dictionary fields."
                )

        return current

    def resolve_reference(
        self,
        reference: str,
        inputs: dict[str, Any],
        step_outputs: dict[str, dict[str, Any]],
    ) -> Any:

        if not isinstance(reference, str):

            raise WorkflowReferenceResolutionError(
                "Reference must be a string."
            )

        parts = reference.split(".")

        if len(parts) < 2:

            raise WorkflowReferenceResolutionError(
                "Invalid workflow reference."
            )

        namespace = parts[0]

        if namespace == "input":

            return self._read_path(
                inputs,
                parts[1:],
            )

        if (
            namespace == "steps"
            and len(parts) >= 4
            and parts[2] == "output"
        ):

            step_id = parts[1]

            if step_id not in step_outputs:

                raise WorkflowReferenceResolutionError(
                    f"Output from step '{step_id}' is unavailable."
                )

            return self._read_path(
                step_outputs[step_id],
                parts[3:],
            )

        raise WorkflowReferenceResolutionError(
            "Unsupported workflow reference namespace."
        )

    def resolve_template(
        self,
        template: Any,
        inputs: dict[str, Any],
        step_outputs: dict[str, dict[str, Any]],
    ) -> Any:

        if isinstance(template, dict):

            if set(template.keys()) == {"$ref"}:

                reference = template["$ref"]

                return self.resolve_reference(
                    reference,
                    inputs,
                    step_outputs,
                )

            return {
                key: self.resolve_template(
                    value,
                    inputs,
                    step_outputs,
                )
                for key, value in template.items()
            }

        if isinstance(template, list):

            return [
                self.resolve_template(
                    item,
                    inputs,
                    step_outputs,
                )
                for item in template
            ]

        return template


workflow_reference_resolver = WorkflowReferenceResolver()