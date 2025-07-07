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
        if parsed.netloc not in ["github.com", "www.github.com"];
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

        async with httpx.AsyncClient(timeout=30.0) as Client:
            response= await Client.get(
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
        
