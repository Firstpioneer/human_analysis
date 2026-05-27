"""GitHub 数字足迹挖掘"""
import re
import base64
import requests
import config


class DigitalFootprintMiner:
    def __init__(self):
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        if config.GITHUB_TOKEN:
            self.headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"

    def extract_links(self, text: str) -> dict:
        links = [link.rstrip(".,;，。；)") for link in re.findall(r'https?://[^\s，,；;）)]+', text)]
        github_links = [link for link in links if re.search(r"github\.com/[A-Za-z0-9_.-]+", link)]
        blogs = [link for link in links if "github.com" not in link]
        repos = []
        username = None
        for link in github_links:
            match = re.search(r"github\.com/([A-Za-z0-9_.-]+)(?:/([A-Za-z0-9_.-]+))?", link)
            if not match:
                continue
            username = username or match.group(1)
            if match.group(2):
                repos.append({
                    "name": f"{match.group(1)}/{match.group(2)}",
                    "url": f"https://github.com/{match.group(1)}/{match.group(2)}",
                })
        return {"username": username, "github_links": github_links, "repos": repos, "blogs": blogs}

    def mine_data(self, text: str) -> dict:
        links = self.extract_links(text)
        username = links["username"]
        blog_data = self._mine_blogs(links["blogs"])
        if not username:
            return {
                "status": "no_footprint_found" if not blog_data else "partial",
                "links": links,
                "blogs": blog_data,
            }
        try:
            user_api = f"https://api.github.com/users/{username}"
            user_resp = requests.get(user_api, headers=self.headers, timeout=5)
            user_resp.raise_for_status()
            user_data = user_resp.json()
            repos_api = f"https://api.github.com/users/{username}/repos?sort=updated"
            repos_resp = requests.get(repos_api, headers=self.headers, timeout=5)
            repos_resp.raise_for_status()
            repos_data = repos_resp.json()
            languages = {}
            repo_summaries = []
            for repo in repos_data[:10]:
                lang = repo.get('language')
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1
                repo_summaries.append({
                    "name": repo.get("full_name"),
                    "url": repo.get("html_url"),
                    "language": lang,
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "updated_at": repo.get("updated_at", ""),
                    "description": repo.get("description") or "",
                    "topics": repo.get("topics", []) or [],
                    "clone_url": repo.get("clone_url") or "",
                })
            public_repos = user_data.get("public_repos", 0)
            activity_signal = "high" if public_repos >= 20 else ("medium" if public_repos >= 5 else "low")
            repository_previews = self._build_repository_previews(repo_summaries)
            return {
                "status": "success",
                "links": links,
                "github_url": f"https://github.com/{username}",
                "public_repos": public_repos,
                "followers": user_data.get("followers", 0),
                "top_languages": sorted(languages.items(), key=lambda x: x[1], reverse=True),
                "recent_repositories": repo_summaries,
                "repository_previews": repository_previews,
                "blogs": blog_data,
                "activity_signal": activity_signal,
            }
        except Exception as e:
            return {"status": "fetch_failed", "error": str(e), "links": links, "blogs": blog_data}

    def _mine_blogs(self, urls: list[str]) -> list[dict]:
        blogs = []
        for url in urls[:5]:
            try:
                resp = requests.get(url, timeout=5, headers={"User-Agent": "AI-Recruiting-Verifier/1.0"})
                title_match = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.I | re.S)
                keyword_match = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\'](.*?)["\']', resp.text, re.I | re.S)
                title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else url
                tags = []
                if keyword_match:
                    tags = [tag.strip() for tag in re.split(r"[,，]", keyword_match.group(1)) if tag.strip()]
                blogs.append({"url": url, "title": title[:120], "tags": tags[:10], "status": "success"})
            except Exception as e:
                blogs.append({"url": url, "status": "fetch_failed", "error": str(e)})
        return blogs

    def _build_repository_previews(self, repos: list[dict]) -> list[dict]:
        previews = []
        for repo in repos[:6]:
            repo_name = repo.get("name")
            if not repo_name:
                continue
            readme = self._fetch_readme(repo_name)
            summary = repo.get("description") or readme.get("summary") or "未提供项目描述"
            tech_stack = []
            if repo.get("language"):
                tech_stack.append(repo["language"])
            tech_stack.extend(repo.get("topics") or [])
            tech_stack.extend(readme.get("tech_stack") or [])
            deduped_stack = []
            for tech in tech_stack:
                if tech and tech not in deduped_stack:
                    deduped_stack.append(tech)
            previews.append({
                "name": repo_name,
                "url": repo.get("url", ""),
                "clone_url": repo.get("clone_url", ""),
                "summary": summary[:180],
                "tech_stack": deduped_stack[:8],
                "stars": repo.get("stars", 0),
                "forks": repo.get("forks", 0),
                "updated_at": repo.get("updated_at", ""),
                "preview_image": self._github_social_preview_url(repo_name),
                "readme_excerpt": readme.get("excerpt", ""),
            })
        return previews

    def _fetch_readme(self, repo_name: str) -> dict:
        try:
            resp = requests.get(
                f"https://api.github.com/repos/{repo_name}/readme",
                headers=self.headers,
                timeout=5,
            )
            resp.raise_for_status()
            payload = resp.json()
            encoded = payload.get("content") or ""
            if payload.get("encoding") != "base64" or not encoded:
                return {}
            text = base64.b64decode(encoded).decode("utf-8", errors="ignore")
            plain = self._markdown_to_text(text)
            return {
                "summary": self._first_meaningful_paragraph(plain),
                "excerpt": plain[:300],
                "tech_stack": self._extract_readme_tech_stack(plain),
            }
        except Exception:
            return {}

    def _markdown_to_text(self, text: str) -> str:
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"!\[[^\]]*]\([^)]+\)", " ", text)
        text = re.sub(r"\[[^\]]+]\([^)]+\)", " ", text)
        text = re.sub(r"^[#>*\-\s]+", "", text, flags=re.M)
        return re.sub(r"\s+", " ", text).strip()

    def _first_meaningful_paragraph(self, text: str) -> str:
        for part in re.split(r"[。.!?]\s+|\n+", text):
            part = part.strip()
            if 20 <= len(part) <= 220:
                return part
        return text[:180]

    def _extract_readme_tech_stack(self, text: str) -> list[str]:
        known = [
            "Python", "Java", "Go", "JavaScript", "TypeScript", "Vue", "React", "Node.js",
            "FastAPI", "Django", "Flask", "Spring Boot", "MySQL", "PostgreSQL", "Redis",
            "Docker", "Kubernetes", "PyTorch", "TensorFlow", "LLM", "RAG",
        ]
        lower = text.lower()
        return [tech for tech in known if tech.lower() in lower][:8]

    def _github_social_preview_url(self, repo_name: str) -> str:
        return f"https://opengraph.githubassets.com/resume-preview/{repo_name}"
