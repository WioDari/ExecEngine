class ExecutionError(RuntimeError):
    """Base error raised by the isolated execution layer."""

class ExecutionConfigurationError(ExecutionError):
    """Non-retriable submission or runtime-manifest configuration error."""

class TransientExecutionError(ExecutionError):
    """Retriable worker infrastructure error."""

class IsolateCleanupError(TransientExecutionError):
    """The isolate sandbox could not be safely cleaned and must not be reused."""