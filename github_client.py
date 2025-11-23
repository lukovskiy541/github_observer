import os
from github import Github
from github.GithubException import GithubException
import logging

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, token=None):
        self.client = Github(token) if token else Github()

    def _normalize_username(self, username: str) -> str:
        """
        Normalizes a GitHub username that may be provided as a full URL
        into a bare username string.

        Examples:
          - 'https://github.com/username' -> 'username'
          - 'github.com/username/' -> 'username'
        """
        username = username.strip()
        if "github.com/" in username:
            username = username.split("github.com/", 1)[-1]
        username = username.split("/", 1)[0]
        return username.strip()

    def _normalize_repo_identifier(self, repo: str) -> str:
        """
        Normalizes various GitHub repository identifiers to 'owner/name' form.

        Supports full URLs like:
          - https://github.com/owner/name
          - https://github.com/owner/name/
        As well as plain 'owner/name' strings.
        """
        repo = repo.strip()
        if "github.com/" in repo:
            repo = repo.split("github.com/", 1)[-1]
        # Strip any trailing slashes or fragments
        repo = repo.split("#", 1)[0].split("?", 1)[0].strip("/")
        return repo

    def get_user_summary(self, username: str) -> str:
        """
        Fetches a summary of a GitHub user, including bio, stats, and a
        broader overview of their repositories.
        """
        try:
            user = self.client.get_user(self._normalize_username(username))
            
            summary = [
                f"User: {user.login} ({user.name})",
                f"Bio: {user.bio}",
                f"Location: {user.location}",
                f"Public Repos: {user.public_repos}",
                f"Followers: {user.followers}",
                f"Profile URL: {user.html_url}",
                "",
                "Repository overview:",
            ]

            # Collect a broad sample of repositories to get a "full picture"
            # while staying within reasonable API and token limits.
            # For most users, this effectively means "all" repos.
            max_repos = 200
            repos = []
            for repo in user.get_repos():
                repos.append(repo)
                if len(repos) >= max_repos:
                    break

            repo_count = len(repos)
            logger.info(f"GitHubClient.get_user_summary: analyzed {repo_count} repos for user {user.login}")

            if not repos:
                summary.append("No public repositories found.")
                return "\n".join(summary)

            # Aggregate languages and basic stats
            language_counts: dict[str, int] = {}
            total_stars = 0
            for repo in repos:
                total_stars += repo.stargazers_count or 0
                lang = repo.language or "Unknown"
                language_counts[lang] = language_counts.get(lang, 0) + 1

            summary.append(f"- Repositories analyzed (sample): {repo_count}")
            summary.append(f"- Total stars across analyzed repos: {total_stars}")

            # Simple language distribution
            summary.append("- Languages (by repo count):")
            for lang, count in sorted(language_counts.items(), key=lambda x: x[1], reverse=True):
                summary.append(f"  • {lang}: {count} repos")

            # Top repositories by stars
            summary.append("\nTop repositories by stars (up to 10):")
            top_star_repos = sorted(
                repos,
                key=lambda r: r.stargazers_count,
                reverse=True
            )[:10]

            for repo in top_star_repos:
                description = repo.description or "No description provided."
                repo_info = [
                    f"- {repo.full_name} (Stars: {repo.stargazers_count}, Language: {repo.language})",
                    f"  Description: {description}",
                    f"  URL: {repo.html_url}",
                ]

                # Try to get README for additional context
                try:
                    readme = repo.get_readme()
                    content = readme.decoded_content.decode("utf-8", errors="ignore")
                    # Truncate readme to avoid hitting token limits too fast
                    repo_info.append(f"  README snippet: {content[:500]}...")
                except GithubException:
                    repo_info.append("  README: Not found")

                summary.extend(repo_info)

            # List all analyzed repositories so the agent can see the broader portfolio,
            # including those without descriptions.
            summary.append("\nAll analyzed repositories:")
            for repo in repos:
                description = repo.description or "No description provided."
                summary.append(
                    f"- {repo.full_name} | Stars: {repo.stargazers_count} | "
                    f"Language: {repo.language} | Description: {description}"
                )

            return "\n".join(summary)

        except GithubException as e:
            logger.error(f"GitHub Error: {e}")
            return f"Error fetching data for user {username}: {e.data.get('message', str(e))}"
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            return f"An unexpected error occurred: {str(e)}"

    def list_user_repositories(self, username: str, max_repos: int = 300) -> str:
        """
        Returns a list of repositories for the given user, including basic
        metadata for each repository.

        This is intended as a machine-readable-but-human-friendly list that
        the AI agent can scan to decide which repos to inspect in more detail.
        """
        try:
            user = self.client.get_user(self._normalize_username(username))

            lines: list[str] = [
                f"Repositories for user: {user.login} ({user.name})",
                f"Total public repos reported by GitHub: {user.public_repos}",
                "",
                f"Listing up to {max_repos} repositories:",
            ]

            count = 0
            for repo in user.get_repos():
                lines.append(
                    f"- {repo.full_name} | Stars: {repo.stargazers_count} | "
                    f"Language: {repo.language} | URL: {repo.html_url}"
                )
                if repo.description:
                    lines.append(f"  Description: {repo.description}")

                count += 1
                if count >= max_repos:
                    break

            if count == 0:
                lines.append("No public repositories found.")

            logger.info(
                f"GitHubClient.list_user_repositories: listed {count} repos "
                f"for user {user.login} (max_repos={max_repos})"
            )

            return "\n".join(lines)

        except GithubException as e:
            logger.error(f"GitHub Error while listing repos: {e}")
            return f"Error listing repositories for user {username}: {e.data.get('message', str(e))}"
        except Exception as e:
            logger.error(f"Unexpected Error while listing repos: {e}")
            return f"An unexpected error occurred while listing repositories: {str(e)}"

    def inspect_repository(
        self,
        repo: str,
        max_files: int = 10,
        max_file_chars: int = 1500,
        path_filter: str | None = None,
    ) -> str:
        """
        Performs a lightweight code-level inspection of a GitHub repository.

        Returns:
            A human-readable summary with basic metadata, a rough file tree,
            and code snippets from a limited number of source files.
        """
        try:
            repo_id = self._normalize_repo_identifier(repo)
            gh_repo = self.client.get_repo(repo_id)

            summary: list[str] = [
                f"Repository: {gh_repo.full_name}",
                f"Description: {gh_repo.description}",
                f"Stars: {gh_repo.stargazers_count}",
                f"Forks: {gh_repo.forks_count}",
                f"Language: {gh_repo.language}",
                f"URL: {gh_repo.html_url}",
                "",
                "Code inspection (limited sample):",
            ]

            # Breadth-first traversal of the repo tree, collecting a limited
            # number of reasonably-sized text files.
            to_visit = [""]
            files_added = 0

            # Extensions that are most useful for technical assessment.
            preferred_exts = {
                ".py", ".js", ".ts", ".tsx", ".jsx",
                ".java", ".go", ".rs", ".rb", ".php",
                ".cs", ".cpp", ".cc", ".c", ".h", ".hpp",
                ".scala", ".kt", ".swift",
                ".sh", ".ps1", ".bash",
                ".sql",
                ".yaml", ".yml", ".toml", ".ini",
                ".ipynb",
            }

            while to_visit and files_added < max_files:
                path = to_visit.pop(0)
                try:
                    contents = gh_repo.get_contents(path or "")
                except GithubException:
                    continue

                if not isinstance(contents, list):
                    contents = [contents]

                for item in contents:
                    if files_added >= max_files:
                        break

                    if item.type == "dir":
                        to_visit.append(item.path)
                        continue

                    # Optional simple path filter (e.g. 'src', 'backend', 'api')
                    if path_filter and path_filter.lower() not in item.path.lower():
                        continue

                    # Skip very large files to avoid huge responses
                    if item.size and item.size > max_file_chars * 4:
                        continue

                    # Prefer source files; skip obvious assets/binaries
                    ext = os.path.splitext(item.path)[1].lower()
                    if preferred_exts and ext not in preferred_exts:
                        continue

                    try:
                        raw = item.decoded_content.decode("utf-8", errors="ignore")
                    except Exception:
                        continue

                    snippet = raw[:max_file_chars]
                    summary.append("")
                    summary.append(f"File: {item.path} (approx. {item.size} bytes)")
                    summary.append("Code snippet:")
                    summary.append(snippet)

                    files_added += 1

            if files_added == 0:
                summary.append("\nNo suitable code files were found with the current limits.")

            return "\n".join(summary)

        except GithubException as e:
            logger.error(f"GitHub Error during repo inspection: {e}")
            return f"Error inspecting repository {repo}: {e.data.get('message', str(e))}"
        except Exception as e:
            logger.error(f"Unexpected Error during repo inspection: {e}")
            return f"An unexpected error occurred while inspecting {repo}: {str(e)}"

    def get_repository_tree(
        self,
        repo: str,
        max_entries: int = 500,
    ) -> str:
        """
        Returns a textual folder/file tree for the given repository.

        The tree is depth-first and limited to max_entries entries to avoid
        overly large responses.
        """
        try:
            repo_id = self._normalize_repo_identifier(repo)
            gh_repo = self.client.get_repo(repo_id)

            lines: list[str] = [
                f"Repository: {gh_repo.full_name}",
                f"URL: {gh_repo.html_url}",
                "",
                f"Folder structure (up to {max_entries} entries):",
            ]

            stack: list[tuple[str, int]] = [("", 0)]
            entries = 0

            while stack and entries < max_entries:
                path, depth = stack.pop()
                try:
                    contents = gh_repo.get_contents(path or "")
                except GithubException:
                    continue

                if not isinstance(contents, list):
                    contents = [contents]

                # Sort to keep directories grouped
                contents.sort(key=lambda c: (c.type != "dir", c.path))

                for item in contents:
                    if entries >= max_entries:
                        break

                    name = os.path.basename(item.path)
                    indent = "  " * depth

                    if item.type == "dir":
                        lines.append(f"{indent}[D] {name}/")
                        # Push directory contents for later
                        stack.append((item.path, depth + 1))
                    else:
                        lines.append(f"{indent}[F] {name}")

                    entries += 1

            if entries >= max_entries:
                lines.append(
                    f"\n(Tree truncated at {max_entries} entries to keep the response manageable.)"
                )

            if entries == 0:
                lines.append("No files or folders found in repository.")

            return "\n".join(lines)

        except GithubException as e:
            logger.error(f"GitHub Error while reading tree: {e}")
            return f"Error getting folder structure for {repo}: {e.data.get('message', str(e))}"
        except Exception as e:
            logger.error(f"Unexpected Error while reading tree: {e}")
            return f"An unexpected error occurred while getting folder structure: {str(e)}"

    def inspect_repository_files(
        self,
        repo: str,
        max_files: int = 200,
        max_chars_per_file: int = 300,
        path_filter: str | None = None,
    ) -> str:
        """
        Returns snippets of code for each file in the repository.

        Each file contributes up to max_chars_per_file characters. Very large
        or binary files may be skipped. The total number of files is limited
        by max_files.
        """
        try:
            # Be defensive: tools may pass these as strings/floats.
            try:
                max_files_int = int(max_files)
            except Exception:
                max_files_int = 200
            try:
                max_chars_int = int(max_chars_per_file)
            except Exception:
                max_chars_int = 300

            repo_id = self._normalize_repo_identifier(repo)
            gh_repo = self.client.get_repo(repo_id)

            lines: list[str] = [
                f"Repository: {gh_repo.full_name}",
                f"URL: {gh_repo.html_url}",
                "",
                f"File snippets (up to {max_files_int} files, {max_chars_int} characters each):",
            ]

            to_visit = [""]
            files_added = 0

            while to_visit and files_added < max_files_int:
                path = to_visit.pop(0)
                try:
                    contents = gh_repo.get_contents(path or "")
                except GithubException:
                    continue

                if not isinstance(contents, list):
                    contents = [contents]

                for item in contents:
                    if files_added >= max_files_int:
                        break

                    if item.type == "dir":
                        to_visit.append(item.path)
                        continue

                    # Optional simple path filter (e.g. 'src', 'backend', 'api')
                    if path_filter and path_filter.lower() not in item.path.lower():
                        continue

                    # Skip very large files/binaries based on size hint
                    if item.size and item.size > max_chars_int * 20:
                        continue

                    try:
                        raw = item.decoded_content.decode("utf-8", errors="ignore")
                    except Exception:
                        continue

                    snippet = raw[:max_chars_int]

                    lines.append("")
                    lines.append(f"File: {item.path} (approx. {item.size} bytes)")
                    lines.append("Snippet:")
                    indented = "\n".join(f"    {ln}" for ln in snippet.splitlines())
                    lines.append(indented)

                    files_added += 1

            if files_added == 0:
                lines.append("\nNo suitable text files were found with the current limits.")

            return "\n".join(lines)

        except GithubException as e:
            logger.error(f"GitHub Error while inspecting files: {e}")
            return f"Error inspecting files for {repo}: {e.data.get('message', str(e))}"
        except Exception as e:
            logger.error(f"Unexpected Error while inspecting files: {e}")
            return f"An unexpected error occurred while inspecting files for {repo}: {str(e)}"
