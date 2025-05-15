import requests
import os


def fetch_github(issue_url):
    # e.g. https://github.com/JodaOrg/joda-time/issues/93
    owner, repo, _, num = issue_url.rstrip('/').split('/')[-4:]
    api = f"https://api.github.com/repos/{owner}/{repo}/issues/{num}"
    token = os.getenv('GITHUB_TOKEN')
    headers = {'Authorization': f'token {token}'} if token else {}
    r = requests.get(api, headers=headers)
    r.raise_for_status()
    j = r.json() or {}
    return j.get('title'), j.get('body')


def fetch_jira(issue_url, user=None, pwd=None):
    # e.g. https://issues.apache.org/jira/browse/CODEC-77
    key = issue_url.rstrip('/').split('/')[-1]
    api = f"https://issues.apache.org/jira/rest/api/2/issue/{key}?fields=summary,description"
    auth = (user, pwd) if user and pwd else None
    r = requests.get(api, auth=auth)
    r.raise_for_status()
    j = r.json() or {}
    f = j.get('fields', {})
    return f.get('summary'), f.get('description')


def fetch_sourceforge(issue_url):
    # e.g. https://sourceforge.net/p/joda-time/bugs/160
    # SF 提供 JSON 端点：
    proj, bug = issue_url.rstrip('/').split('/')[-3], issue_url.split('/')[-1]
    api = f"https://sourceforge.net/rest/p/{proj}/bugs/{bug}?format=json"
    r = requests.get(api)
    r.raise_for_status()
    j = r.json() or {}
    t = j.get('ticket', {})
    return t.get('summary'), t.get('description')


def fetch_googlecode(json_url):
    # e.g. https://storage.googleapis.com/google-code-archive/v2/code.google.com/closure-compiler/issues/issue-253.json
    r = requests.get(json_url)
    r.raise_for_status()
    j = r.json() or {}
    # 取出 summary 字段
    summary = j.get('summary')
    # comments 通常是一个列表，第 0 项即最初提交的内容
    comments = j.get('comments', [])
    description = comments[0].get('content') if comments else None
    return summary, description


def fetch_googlecode_archive(issue_url):
    # e.g. https://code.google.com/archive/p/mockito/issues/200
    # 从 URL 中拆出项目名和 issue 编号
    parts = issue_url.rstrip('/').split('/')
    # parts[-4] == 'p', parts[-3] == '{project}', parts[-1] == '{num}'
    proj = parts[-3]
    num = parts[-1]
    # 构造 JSON API 端点（参考 closure-compiler 的存储路径格式）
    api = (
        f"https://storage.googleapis.com/"
        f"google-code-archive/v2/code.google.com/{proj}/issues/issue-{num}.json"
    )
    # 发起请求
    r = requests.get(api)
    r.raise_for_status()
    j = r.json() or {}
    # 取出 summary 字段
    summary = j.get('summary')
    # comments 通常是一个列表，第 0 项即最初提交的内容
    comments = j.get('comments', [])
    description = comments[0].get('content') if comments else None
    return summary, description


def fetch_issue(issue_url, user=None, pwd=None):
    """
    根据 issue_url 的类型调用不同的 API 获取标题和描述
    """
    if issue_url.startswith('https://github.com'):
        fetched = fetch_github(issue_url)
    elif issue_url.startswith('https://issues.apache.org/jira'):
        fetched = fetch_jira(issue_url, user, pwd)
    elif issue_url.startswith('https://sourceforge.net'):
        fetched = fetch_sourceforge(issue_url)
    elif issue_url.startswith('https://storage.googleapis.com/google-code-archive'):
        fetched = fetch_googlecode(issue_url)
    elif issue_url.startswith('https://code.google.com/archive/p'):
        fetched = fetch_googlecode_archive(issue_url)
    else:
        raise ValueError("Unsupported issue URL format")

    if fetched:
        title, description = fetched
        if not title and not description:
            raise ValueError("Title and description is empty")
        return title, description
    else:
        raise ValueError("Failed to fetch issue data")


if __name__ == "__main__":
    # 检查全部四个 URL 的处理
    urls = [
        "https://github.com/JodaOrg/joda-time/issues/93",
        "https://issues.apache.org/jira/browse/CODEC-77",
        "https://sourceforge.net/p/joda-time/bugs/160",
        "https://storage.googleapis.com/google-code-archive/v2/code.google.com/closure-compiler/issues/issue-253.json",
        "https://code.google.com/archive/p/mockito/issues/200",
    ]
    for url in urls:
        print("Fetching issue from:", url)
        try:
            title, description = fetch_issue(url)
            print(f"Title: {title}\nDescription:\n{description}\n")
        except Exception as e:
            print(f"Error fetching issue from {url}: {e}")
