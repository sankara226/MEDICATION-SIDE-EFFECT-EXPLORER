"""Upload the app to a Hugging Face Space.

Usage (from the project root):
    pip install huggingface_hub
    huggingface-cli login                       # paste a token with "write" access
    python deploy/deploy_to_hf.py YOUR_HF_USERNAME/medication-side-effect-explorer
"""

import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
FILES = ["app.py", "requirements.txt", "med_explorer/__init__.py",
         "med_explorer/api.py", "med_explorer/analysis.py", "med_explorer/charts.py"]


def main():
    if len(sys.argv) != 2 or "/" not in sys.argv[1]:
        sys.exit(__doc__)
    space = sys.argv[1]

    api = HfApi()
    api.create_repo(space, repo_type="space", space_sdk="gradio", exist_ok=True)

    for path in FILES:
        api.upload_file(path_or_fileobj=ROOT / path, path_in_repo=path,
                        repo_id=space, repo_type="space")
    # The Space reads its settings from the YAML header of its own README
    api.upload_file(path_or_fileobj=ROOT / "deploy" / "space_README.md", path_in_repo="README.md",
                    repo_id=space, repo_type="space")

    print(f"Done: https://huggingface.co/spaces/{space}")
    print("Optional: add an OPENFDA_API_KEY secret in the Space settings to lift the 1,000 requests/day limit.")


if __name__ == "__main__":
    main()
