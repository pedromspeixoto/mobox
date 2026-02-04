from datetime import datetime
from pathlib import Path


def load_prompt(filename: str, workspace: str = None, prompts_dir: Path = None) -> str:
    """Load a prompt from the prompts directory.

    Args:
        filename: Name of the prompt file
        workspace: Optional workspace path to inject into prompt
    """
    if prompts_dir is None:
        prompts_dir = Path(__file__).parent / "prompts"

    prompt_path = prompts_dir / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    # Replace {workspace} placeholder with actual workspace path
    if workspace:
        content = content.replace("{workspace}", workspace)

    # Replace {date} placeholder with current date
    now = datetime.now()
    content = content.replace("{date}", now.strftime("%B %d, %Y"))
    content = content.replace("{year}", str(now.year))

    return content