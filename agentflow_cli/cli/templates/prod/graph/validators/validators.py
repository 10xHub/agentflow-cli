from agentflow.utils.validators import PromptInjectionValidator


prompt_validator = PromptInjectionValidator(
    strict_mode=True,
    max_length=1000,
    blocked_patterns=[],
    suspicious_keywords=[
        "ignore previous",
        "forget previous",
        "disregard previous",
        "bypass",
        "circumvent",
        "override",
        "disable",
        "remove restrictions",
        "token",
        "coupon",
        "free",
    ],
)
