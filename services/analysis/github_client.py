import requests
import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

ERROR_CODE = {
    404: "REPO_NOT_FOUND",
    401: "GITHUB_TOKEN_INVALID",
    403: "RATE_LIMIT_EXCEEDED",
    409: "EMPTY_GITHUB_REPO",
    503: "SERVICE_UNAVAILABLE",
    500: "INTERNAL_SERVER_ERROR"
}

_github_token = None

def _is_running_on_aws() -> bool:
    """
    Function to determine if the current code is running on AWS as Lambda or local machine

    Returns:
        bool: True if running on AWS else False
    """
    # AWS_LAMBDA_RUNTIME_API is initialized when lambda is running on AWS [only valid for AWS Lambda Services]
    return "AWS_LAMBDA_RUNTIME_API" in os.environ


def _get_credentials() -> str:
    """
    Returns the GitHub Credential

    Returns: 
        str: github_token if present, else None
    """
    # Check if the github token is fetched already
    global _github_token
    if _github_token is not None:
        return _github_token
    # Determine if we are running the function locally or on AWS Lambda
    is_aws = _is_running_on_aws()
    
    if is_aws:
        # Go to SSM to get the credentials
        logger.info("Running on AWS instance. Fetching tokens from AWS")
        github_param_name = os.environ.get("GITHUB_PARAM_NAME")

        if not github_param_name:
            logger.error("GITHUB_PARAM_NAME environment variable not set")
            return None
        
        # Get credentials from AWS SSM
        ssm_client = boto3.client('ssm')
        
        try:
            response = ssm_client.get_parameter(
                Name=github_param_name,
                WithDecryption=True
            )

            _github_token = response['Parameter']['Value']
            logger.info("Successfully retrieved GitHub token from AWS")
        
        except ClientError as e:
            logger.error(f"Error fetching parameter {github_param_name}: {e}")
            return None

    else:
        logger.info("Running locally - loading from .env")
        try:
            from dotenv import load_dotenv
            load_dotenv()
            _github_token = os.environ.get("GITHUB_TOKEN")
            if not _github_token:
                logger.warning("GITHUB_TOKEN not found in environment")
        except ImportError:
            logger.warning(f"python-dotenv not found. Ensure it's installed for Local Environment")
            return None
    
    return _github_token

def create_response(status_code: int, data: dict = None, error_code: str = None) -> dict:
    """
    Creates the response for all the requests made

    Args:
        status_code: int: HTTP Status Code
        data: dict: response payloaf for successful requests
        error_code: str: Error Identifier for failed requests

    Returns:
        Standardized Response Dictionary
    """
    body = {}

    if status_code >= 400:
        body["error_code"] = error_code or ERROR_CODE.get(status_code, "UNKNOWN_ERROR")
    else:
        body["data"] = data

    return {
        "statusCode": status_code,
        "body": body
    }


def _get_headers() -> dict:
    """
    Returnes headers for GitHub API
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Demo-Builder",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    token = _get_credentials()

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers

        
def get_repo_metadata(owner: str, repo: str) -> dict:
    """
    Calls the GitHub API to fetch the Repo data

    Args:
        owner: str: name of the owner
        repo: str: name of the repo

    Returns: 
        dict: statusCode and body containing repo metadata or error
    """
    # Configuring the request
    # GitHub API
    GITHUB_API = f"https://api.github.com/repos/{owner}/{repo}"

    # Getting the headers for the API call
    headers = _get_headers()
    
    try:
        response = requests.get(GITHUB_API, headers=headers, timeout=10)

        # if there is an error response
        if response.status_code != 200:
            logger.warning(f"GitHub API returned {response.status_code} for {owner}/{repo}")
            return create_response(response.status_code)
        
        response_data = response.json()
        logger.info(f"Successfully fetched metadata for {owner}/{repo}")

        return create_response(200, data={
            "name": response_data.get("name"),
            "description": response_data.get("description"),
            "stars": response_data.get("stargazers_count"),
            "topics": response_data.get("topics", []),
            "default_branch": response_data.get("default_branch"),
            "language": response_data.get("language"),
            "html_url": response_data.get("html_url")
        })

    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching metadata for {owner}/{repo}")
        return create_response(503, error_code="REQUEST_TIMEOUT")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error for {owner}/{repo}")
        return create_response(503, error_code="CONNECTION_ERROR")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {owner}/{repo}: {e}")
        return create_response(500)
    

def get_latest_commit_sha(owner: str, repo: str, default_branch: str) -> str:
    """
    Calls the GitHub API to fetch the latest commit sha for the default branch

    Args:
        owner: str: name of the owner of the repository
        repo: str: name of the repository
        default_branch: str: name of the latest branch of the repository
    
        Returns:
            str: latest SHA Commit for the given repository
    """
    LATEST_COMMIT_API = f"https://api.github.com/repos/{owner}/{repo}/commits/{default_branch}"
    
    try:
        # Getting the headers for the api call
        headers = _get_headers()

        # Making the API call
        response = requests.get(LATEST_COMMIT_API, headers=headers, timeout=10)

        # If there is issue with the request
        if response.status_code != 200:
            return create_response(status_code=response.status_code)

        response_data = response.json()
        
        return create_response(200, data = {
            "latest_commit_sha": response_data.get("sha")
        })
    
    except requests.exceptions.Timeout:
        return create_response(503, error_code="REQUEST_TIMEOUT")
    except requests.exceptions.ConnectionError:
        return create_response(503, error_code="CONNECTION_ERROR")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed 'Get Lastest SHA' request. Error: {e}")
        return create_response(500)
    

def get_file_tree(owner: str, repo: str, branch: str):
    """
    Calls the GitHub API to get the tree of a given branch

    Args:
        owner: str: name of the owner of teh GitHub Repository
        repo: str: name of the repository
        branch: str: name of the branch we want to get the tree of

    Returns:
        dict: returns dictionary of the tree of the branch
    """
    logger.info(f"Fetching file tree for {owner}/{repo}@{branch}")
    GITHUB_TREE_API = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    
    # Getting the headers for the API call
    headers = _get_headers()

    try:
        # Making the API call
        response = requests.get(GITHUB_TREE_API, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.warning(f"Tree API returned {response.status_code}")
            return create_response(status_code=response.status_code)
        
        response_data = response.json()
        tree = response_data.get("tree", [])

        files = [
            {
                "path": item["path"],
                "size": item.get("size", 0)
            }
            for item in tree if item["type"] == "blob"
        ]

        logger.info(f"Found {len(files)} files in {owner}/{repo}")

        return create_response(200, data= {
            "files": files,
            "truncated" : response_data.get("truncated", False),
            "file_count": len(files)
        })
    
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching tree for {owner}/{repo}")
        return create_response(503, error_code="REQUEST_TIMEOUT")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching tree for {owner}/{repo}")
        return create_response(503, error_code="CONNECTION_ERROR")
    except requests.exceptions.RequestException as e:
        logger.error(f"Tree request failed: {e}")
        return create_response(500)


def get_file_content(owner: str, repo: str, path: str, max_size: int = 100000) -> dict:
    """
    Fetches raw contents of a specific file from GitHub

    Args:
        owner: str: name of the owner of the repo
        repo: str: name of the repository
        path: str: file path (e.g., "src/index.js")

    Returns:
        dict: status code and body containing file content or error
    """
    logger.debug(f"Fetching content for {path}")

    CONTENT_API = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    headers = _get_headers()
    # Request raw content directly
    headers["Accept"] = "application/vnd.github.raw"

    try:
        response = requests.get(CONTENT_API, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.warning(f"Content API returned {response.status_code} for {path}")
            return create_response(status_code=response.status_code)
        
        content = response.text
        logger.debug(f"Fetched {len(content)} bytes for {path}")


        if len(content) > max_size:
            logger.info(f"Skipping the file: {path} because File is too large")
            return create_response(200, data={
                "path": path, 
                "content": None,
                "size": len(content),
                "skipped": True,
                "reason": "FILE_TOO_LARGE"
            })

        return create_response(200, data= {
            "path": path,
            "content": content,
            "size": len(content),
            "skipped": False
        })
    
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching content for {path}")
        return create_response(503, error_code="REQUEST_TIMEOUT")
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching {path}")
        return create_response(503, error_code="CONNECTION_ERROR")
    except requests.exceptions.RequestException as e:
        logger.error(f"Content request failed for {path}: {e}")
        return create_response(500)
