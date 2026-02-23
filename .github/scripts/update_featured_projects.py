"""Fetch pinned repositories from GitHub and update the Featured Projects section in README.md."""

import os
import re
import sys
import urllib.request
import urllib.error
import json

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
USERNAME = os.environ.get("GITHUB_USERNAME", "hndko")
README_PATH = os.environ.get("README_PATH", "README.md")

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query PinnedRepos($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: [REPOSITORY]) {
      nodes {
        ... on Repository {
          name
          description
          url
          primaryLanguage {
            name
          }
          stargazerCount
          forkCount
        }
      }
    }
  }
}
"""

START_MARKER = "<!-- PINNED_REPOS_START -->"
END_MARKER = "<!-- PINNED_REPOS_END -->"


def fetch_pinned_repos():
    payload = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": "bearer " + GITHUB_TOKEN,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP error fetching pinned repos: {e.code} {e.reason}", file=sys.stderr)
        sys.exit(1)

    nodes = data.get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])
    if "errors" in data:
        for err in data["errors"]:
            print(f"GraphQL error: {err.get('message', err)}", file=sys.stderr)
        sys.exit(1)
    return nodes


def build_table(repos):
    if not repos:
        return "| Project | Description | Language |\n| ------- | ----------- | -------- |\n"

    lines = [
        "| Project | Description | Language |",
        "| ------- | ----------- | -------- |",
    ]
    for repo in repos:
        name = repo.get("name", "")
        description = repo.get("description") or ""
        url = repo.get("url", "")
        language = (repo.get("primaryLanguage") or {}).get("name") or "—"
        stars = repo.get("stargazerCount", 0)
        forks = repo.get("forkCount", 0)
        stars_badge = f"⭐ {stars}" if stars > 0 else ""
        forks_badge = f"🍴 {forks}" if forks > 0 else ""
        badges = " ".join(filter(None, [stars_badge, forks_badge]))
        description_cell = f"{description} {badges}".strip() if badges else description
        lines.append(f"| **[{name}]({url})** | {description_cell} | {language} |")

    return "\n".join(lines) + "\n"


def update_readme(table_content):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{table_content}{END_MARKER}"

    if not pattern.search(content):
        print("Markers not found in README. Skipping update.", file=sys.stderr)
        sys.exit(1)

    new_content = pattern.sub(replacement, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("README updated successfully.")


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    repos = fetch_pinned_repos()
    table = build_table(repos)
    update_readme(table)
