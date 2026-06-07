"""Print the resolved configuration for the current environment.

Usage:
    python -m scripts.print_settings
"""

from __future__ import annotations

import json

from supervisor.config import get_settings


def main() -> None:
    settings = get_settings()
    print(json.dumps(settings.model_dump(mode="json"), indent=2, default=str))


if __name__ == "__main__":
    main()
