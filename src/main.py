"""Infrastructure-only application entrypoint."""

from src.config import load_settings
from src.obs import configure_logging


def main() -> None:
    configure_logging()
    settings = load_settings()
    print("Agents Everywhere infrastructure")
    for name, configured in settings.services.items():
        print(f"- {name}: {'configured' if configured else 'missing'}")


if __name__ == "__main__":
    main()
