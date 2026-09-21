from __future__ import annotations

from abc import ABC, abstractmethod

from automation_models import (
    AutomationFramework,
    AutomationLanguage,
)

from automation_plan_resolver import (
    ResolvedAutomationPlan,
)


class BaseFrameworkGenerator(ABC):

    framework: AutomationFramework
    language: AutomationLanguage

    @abstractmethod
    def generate(
        self,
        plan: ResolvedAutomationPlan,
    ) -> str:
        """
        Convert a resolved automation plan into executable
        framework/language-specific source code.
        """
        raise NotImplementedError