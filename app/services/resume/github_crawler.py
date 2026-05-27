"""GitHub 数字足迹挖掘"""
import re
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
                })
            public_repos = user_data.get("public_repos", 0)
            activity_signal = "high" if public_repos >= 20 else ("medium" if public_repos >= 5 else "low")
            return {
                "status": "success",
                "links": links,
                "github_url": f"https://github.com/{username}",
                "public_repos": public_repos,
                "followers": user_data.get("followers", 0),
                "top_languages": sorted(languages.items(), key=lambda x: x[1], reverse=True),
                "recent_repositories": repo_summaries,
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
