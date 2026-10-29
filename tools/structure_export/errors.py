"""Errors raised by the structure exporter. Every rejection names what was refused and why."""


class ExportError(Exception):
    """Base class: the input cannot be converted as configured."""


class ConfigError(ExportError):
    """The structure config is missing, malformed, or inconsistent with its source."""


class SchemError(ExportError):
    """The .schem file violates the Sponge v3 layout."""


class BlockStateError(ExportError):
    """A block or block state does not exist in the target Minecraft version."""


class UnsupportedFeature(ExportError):
    """The input uses a feature this exporter does not convert yet (see FEATURE_HANDLERS)."""

    def __init__(self, feature: str, message: str):
        super().__init__(f"unsupported feature '{feature}': {message}")
        self.feature = feature
