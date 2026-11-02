__all__ = ["AssistentCore", "run_core"]


def __getattr__(name: str):
    if name in __all__:
        from src.core.assistant_core import AssistentCore, run_core

        return {
            "AssistentCore": AssistentCore,
            "run_core": run_core,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
