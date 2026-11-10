from dataclasses import dataclass, field

from app.evaluation.llm.schemas import EvaluationCase


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    version: str
    template: str
    description: str = ""

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Prompt name cannot be empty")
        if not self.version.strip():
            raise ValueError("Prompt version cannot be empty")
        if not self.template.strip():
            raise ValueError("Prompt template cannot be empty")

    def render(self, **variables: str) -> str:
        try:
            return self.template.format(**variables)
        except KeyError as exc:
            raise ValueError(
                f"Missing prompt variable: {exc.args[0]}"
            ) from exc


class PromptRegistry:
    def __init__(self):
        self._templates: dict[tuple[str, str], PromptTemplate] = {}

    def register(self, prompt: PromptTemplate) -> None:
        key = (prompt.name, prompt.version)
        if key in self._templates:
            raise ValueError(f"Prompt already registered: {key}")
        self._templates[key] = prompt

    def get(self, name: str, version: str) -> PromptTemplate:
        try:
            return self._templates[(name, version)]
        except KeyError as exc:
            raise KeyError(
                f"Prompt not found: {name} version {version}"
            ) from exc

    def list_prompts(self) -> list[PromptTemplate]:
        return list(self._templates.values())


@dataclass
class EvaluationDataset:
    name: str
    cases: list[EvaluationCase] = field(default_factory=list)

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Dataset name cannot be empty")
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("Dataset case IDs must be unique")
        if not all(isinstance(case, EvaluationCase) for case in self.cases):
            raise TypeError("All dataset entries must be EvaluationCase objects")

    def add_case(self, case: EvaluationCase) -> None:
        if not isinstance(case, EvaluationCase):
            raise TypeError("case must be an EvaluationCase")
        if any(existing.case_id == case.case_id for existing in self.cases):
            raise ValueError(f"Duplicate case ID: {case.case_id}")
        self.cases.append(case)

    def __len__(self) -> int:
        return len(self.cases)
