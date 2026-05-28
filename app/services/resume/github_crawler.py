"""GitHub 数字足迹挖掘"""
import re
import requests


class DigitalFootprintMiner:
    def __init__(self):
        self.headers = {'Accept': 'application/vnd.github.v3+json'}

    def extract_github_url(self, text: str) -> str:
        match = re.search(r'https?://(?:www\.)?github\.com/([a-zA-Z0-9-]+)', text)
        return match.group(1) if match else None

    def mine_data(self, text: str) -> dict:
        username = self.extract_github_url(text)
        if not username:
            return {"status": "no_footprint_found"}
        try:
            user_api = f"https://api.github.com/users/{username}"
            user_data = requests.get(user_api, headers=self.headers, timeout=5).json()
            repos_api = f"https://api.github.com/users/{username}/repos?sort=updated"
            repos_data = requests.get(repos_api, headers=self.headers, timeout=5).json()
            languages = {}
            for repo in repos_data[:10]:
                lang = repo.get('language')
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1
            return {
                "status": "success",
                "github_url": f"https://github.com/{username}",
                "public_repos": user_data.get("public_repos", 0),
                "followers": user_data.get("followers", 0),
                "top_languages": sorted(languages.items(), key=lambda x: x[1], reverse=True),
                "activity_signal": "high" if user_data.get("public_repos", 0) > 10 else "medium"
            }
        except Exception as e:
            return {"status": "fetch_failed", "error": str(e)}
