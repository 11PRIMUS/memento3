from app.core.config import settings
from app.core.logging import get_logger
from app.models.commit import Commit
from datetime import datetime
import httpx
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlparse

logger= get_logger(__name__)

class Github_service:
    def __init__(self):
        self.base_url ="https://api.github.com"
        self.headers={
            "Accept":"application/vnd.github.v3+json",
            "User-Agent":f"{settings.APP_NAME}/{settings.VERSION}"

        }
        if settings.GITHUB_TOKEN:
            self.headers["Authorization"]=f"token {settings.GITHUB_TOKEN}"
            logger.info("github service intialized")

        else:
            logger.warnigs("github service initialized (limited rate)")
    
    def github_url(self, url: str)-> Tuple[str,str]:
        parsed =urlparse(str(url))
        if parsed.netloc not in ["github.com", "www.github.com"]:
            raise ValueError("invalid github url")
        
        path_parts =parsed.path.strip('/').split('/')
        if len(path_parts) <2:
            raise ValueError("invalid github repository")
        
        owner =path_parts[0]
        repo =path_parts[1].replace('.git','')

        logger.debug("parsed github url", owner=owner, repo= repo)
        return owner, repo
    
    async def get_repoInfo(self, repo_url: str)-> Dict:
        """repo metadata"""
        owner, repo = self.github_url(repo_url)

        logger.info("fetching repository ifo", owner= owner, repo= repo)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response= await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers = self.headers
            )
            if response.status_code ==404:
                logger.error("Repository not found", owner=owner, repo=repo)
                raise ValueError("Repository not found")
            elif response.status_code != 200:
                logger.error("GitHub API error", status_code=response.status_code)
                raise Exception(f"GitHub API error: {response.status_code}")
            
            data = response.json()
            
            logger.info("Repository info fetched", owner=owner, repo=repo, 
                       stars=data.get("stargazers_count", 0))
            
            return {
                "name": data["name"],
                "owner": data["owner"]["login"],
                "description": data.get("description"),
                "default_branch": data.get("default_branch", "main"),
                "github_id": data["id"],
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "language": data.get("language"),
                "is_private": data.get("private", False)
            }
    
    async def get_commits(self, repo_url: str, max_commits: int =100)-> List[Commit]:
        #fetch commit history from github
        owner, repo =self.github_url(repo_url)

        logger.info("starting commit fetch", owner=owner, repo= repo, max_commits= max_commits)

        commits=[]
        page=1
        per_page=min(100, max_commits)

        async with httpx.AsyncClient(timeout=60.0) as client:
            while len(commits) < max_commits:
                logger.debug("fetching commit page", page=page, current_count= len(commits))
                response = await client.get(
                    f"{self.base_url}/repos/{owner}/{repo}/commits",
                    headers= self.headers,
                    params={
                        "per_page":per_page,
                        "page":page
                    }
                )

                if response.status_code != 200:
                    logger.error("failed to fetch commit page", page=page, status_code= response.status_code)
                    break

                page_commits = response.json()
                if not page_commits:
                    logger.info("No more commits found", page=page)
                    break
                
                #process commits from this page
                for commit_data in page_commits:
                    if len(commits) >= max_commits:
                        break
                    
                    commit_detail = await self._get_commit_details(client, owner, repo, commit_data["sha"])
                    if commit_detail:
                        commits.append(commit_detail)
                
                page += 1
                
                if len(page_commits) < per_page:
                    break
        
        logger.info("commit fetch completed", owner=owner, repo=repo, total_commits=len(commits))
        return commits
    
    async def get_commitDetails(self, client:httpx.AsyncClient, owner: str, repo: str, sha: str)-> Optional[Commit]:
        #detailed commit information
        try:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}",
                headers= self.headers
            )
            if response.status_code!= 200:
                logger.warnig("failed to fetch commit details", sha= sha[:8])
                return None
            
            data = response.json()

            return Commit(
                sha=sha,
                message=data["commit"]["message"],
                author=data["commit"]["author"]["name"],
                author_email=data["commit"]["author"]["email"],
                commit_date=datetime.fromisoformat(
                    data["commit"]["author"]["date"].replace("Z", "+00:00")
                ),
                additions=data["stats"]["additions"],
                deletions=data["stats"]["deletions"],
                files_changed=[file["filename"] for file in data.get("files", [])]
            )
        except Exception as e:
            logger.error("error processing commit", sha= sha[:8], error=str(e))
            return None

    async def get_commitDiff(self, repo_url: str, sha: str) -> Optional[str]:
        """Get diff content for a specific commit"""
        owner, repo = self.parse_github_url(repo_url)
        
        logger.debug("Fetching commit diff", owner=owner, repo=repo, sha=sha[:8])
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}",
                headers={
                    **self.headers,
                    "Accept": "application/vnd.github.v3.diff"
                }
            )
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error("failed to fetch commit diff", sha=sha[:8], 
                           status_code=response.status_code)
                return None
        
    async def get_rateLimit(self)-> Dict:
            #ratelimit status for github
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/rate_limit",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("failed to fetch rate limit", status_code=response.status_code)
                return {}
            
    async def search_repo(self, query: str, limit: int = 10) -> List[Dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response =await client.get(
                f"{self.base_url}/search/repositories",
                headers=self.headers,
                params={
                    "q":query,
                    "sort": "stars",
                    "order":"desc",
                    "per_page": limit
                }
            )
            
            if response.status_code ==200:
                data =response.json()
                return data.get("items", [])
            else:
                logger.error("Repository search failed", status_code=response.status_code)
                return []
    
    def test_connection(self) -> bool: #github api connection test
        try:
            import asyncio
            async def _test():
                rate_limit =await self.get_rate_limit()
                return bool(rate_limit.get("rate"))
            
            return asyncio.run(_test())
        except Exception as e:
            logger.error("GitHub service test failed", error=str(e))
            return False