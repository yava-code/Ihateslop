import re
import requests

def parse_github_url(url: str):
    match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None

def fetch_pr_diff(owner: str, repo: str, number: str) -> str:
    headers = {
        "User-Agent": "SloppyDiff-App",
        "Accept": "application/vnd.github.v3.diff"
    }
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.text
        if r.status_code == 403:
            # Rate limit or forbidden, try fallback to .diff URL
            fb_url = f"https://github.com/{owner}/{repo}/pull/{number}.diff"
            fr = requests.get(fb_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if fr.status_code == 200:
                return fr.text
            raise Exception("GitHub API rate limit exceeded and fallback failed.")
        raise Exception(f"GitHub API returned status code {r.status_code}")
    except Exception as e:
        # Fallback to direct .diff file download if API fails
        try:
            fb_url = f"https://github.com/{owner}/{repo}/pull/{number}.diff"
            fr = requests.get(fb_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if fr.status_code == 200:
                return fr.text
        except:
            pass
        raise e
