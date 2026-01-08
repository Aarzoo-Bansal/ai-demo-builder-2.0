import requests
import boto3
import os
import json
import logging

from decimal import Decimal
from datetime import datetime, timedelta

from github_client import get_repo_metadata, get_latest_commit_sha, get_file_tree, get_file_content
from file_scorer import get_high_value_files
from gemini_client import generate_suggestions, select_important_files

# Initialize dynamodb
dynamodb = boto3.resource('dynamodb')
cache_table = dynamodb.Table(os.environ.get('CACHE_TABLE_NAME'))

# Number of days after which the cached entry will be deleted in the Cache table
CACHE_TTL_DAYS = 7

# Minimum number of files threshold for hybrid approach
MIN_FILES_THRESHOLD = 5

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

def parse_github_url(github_url: str) -> tuple:
    """
    Parse GitHub URL to extract owner and repo

    Args:
        github_url: str: github url e.g.(https://github.com/facebook/react)
    
    Returns:
        tuple of the repo name and owner (owner, repo)
    """
    # Removing the last '/' if present
    url = url.rstrip('/')
    parts = url.split('/')

    owner = parts[-2]
    repo = parts[-1]

    if repo.endswith('.git'):
        repo = repo[:-4] # skip the last four letters (.git)

    return (owner, repo)


def get_from_cache(cache_key: str, commit_sha: str) -> dict:
    """
    Check cache for existing analysis

    Args:
        cache_key: str: GitHub repository URL
        commit_sha: str: Latest Commit SHA

    Returns:
        dict of Cached data or None
    """
    try:
        response = cache_table.get_item(
            Key={
                'repo_url': cache_key,
                'commit_sha': commit_sha
            }
        )

        if 'Item' in response:
            logger.info(f"Cache Hit for repo: {cache_key}")
            return response["Item"]
        
        logger.info(f"Cache MISS for {cache_key}")
        return None
    
    except Exception as e:
        logger.error(f"Cache Lookup Error: {e}")
        return None


def save_to_cache(cache_key: str, commit_sha: str, analysis: dict, suggestions: list) -> bool:
    """
    Save analysis results to cache

    Args:
        cache_key: str: GitHub repository URL [format: {owner.lower()}/{repo.lower()}]
        commit_sha: Latest commit SHA
        analysis: Repository analysis data
        suggestions: Video suggestions from Gemini

    Returns:
        True if successful, else False
    """
    try:
        # creating a time stamp for 7 days, as we will keep the data in cache table only for 7 days and then delete it
        ttl = int((datetime.now() + timedelta(days=CACHE_TTL_DAYS)).timestamp())

        cache_table.put_item(
            Item={
                'repo_url': cache_key,
                'commit_sha': commit_sha,
                'analysis': analysis,
                'suggestions': suggestions,
                'created_at': datetime.now().isoformat(),
                'ttl': ttl
            }
        )

        logger.info(f"Cached results for {cache_key}")
        return True

    except Exception as e:
        logger.error(f"Cache save error for repo {cache_key}")
        return False


def handler(event, context):
    """
    Main Lambda handler

    Input: { "github_url": "https://github.com/owner/repo" }
    Output: { "analysis": {...}, "suggestions": [...] }
    """
    logger.loggin(f"Received event: {json.dumps(event)}")

    # ============================================
    # STEP 1: Parse Input
    # ============================================
    # get the github link
    github_url = event.get('github_url', None)

    if not github_url:
        return {"statusCode": 400,
                "body": {"error_code": "MISSING_GITHUB_URL"}
        }
    
    owner, repo = parse_github_url(github_url=github_url)
    cache_key = f"{owner.lower()}/{repo.lower()}"

    if not owner or not repo:
        return {
            "statusCode": 400,
            "body": {"error_code": "INVALID_GITHUB_URL"}
        }
    
    logger.info(f"Analysing: {owner}/{repo}")

    # ============================================
    # STEP 2: Get Repository Metadata
    # ============================================
    metadata_response = get_repo_metadata(owner=owner, repo=repo)

    if metadata_response["statusCode"] != 200:
        return metadata_response
    
    metadata = metadata_response["body"]["data"]
    default_branch = metadata.get("default_branch", "main")

    logger.info(f"Repository: {metadata.get('name')}, Branch: {default_branch}")

    # ============================================
    # STEP 3: Get Latest Commit SHA
    # ============================================
    commit_response = get_latest_commit_sha(owner=owner, repo=repo, default_branch=default_branch)

    if commit_response["statusCode"] != 200:
        logging.error(f"Could not get SHA for {owner}/{repo}. Skipping Cache")
        commit_sha = None
    
    else:
        commit_sha = commit_response["body"]["data"]["sha"]
        logging.info(f"Latest Commit SHA for {owner}/{repo} is {commit_sha}")
    

    # ============================================
    # STEP 4: Check Cache
    # ============================================
    if commit_sha:
        cached = get_from_cache(cache_key=cache_key, commit_sha=commit_sha)

        # If entry is found in the cache table, return that. We do not need to call gemini again to analyse the repository
        if cached:
            return {
                "analysis": cached.get("analysis"),
                "suggestions": cached.get("suggestions"),
                "from_cache": True
            }
    
    # ============================================
    # STEP 5: Get File Tree - list of files in the repository
    # ============================================
    tree_response = get_file_tree(owner=owner, repo=repo, branch=default_branch)

    if tree_response["statusCode"] != 200:
        return tree_response

    all_files = tree_response["body"]["data"]["files"]
    file_count = tree_response["body"]["data"]["file_count"]

    logger.info(f"Found {file_count} files in {owner}/{repo}")

    if file_count == 0:
        return {
            "statusCode": 400,
            "body": {"error_code": "EMPTY_REPOSITORY"}
        }
    
    # ============================================
    # STEP 6: Filter High-Value Files (Hybrid)
    # ============================================
    high_value_files = get_high_value_files(all_files, max_files=10)
    selection_method = "rule-based"

    logger.info(f"Rule-based scoring found {len(high_value_files)} files: {high_value_files}")

    # Hybrid: Use AI if rule-based found insufficient files
    if len(high_value_files) < MIN_FILES_THRESHOLD:
        logger.info(f"Only {len(high_value_files)} files from rules, trying AI selection...")
        ai_selected = select_important_files(files=all_files, max_files=10)

        if ai_selected:
            # Merge unique files from both approaches
            combined = list(set(high_value_files + ai_selected))[:10]
            
            if len(combined) > len(high_value_files):
                high_value_files = combined
                selection_method = "hybrid"
            else:
                logging.info("AI found no additional files, keeping rule-based results")
                
    # If both AI and rule based found no files 
    if len(high_value_files) == 0 and file_count > 0:
        fallback_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c'}
        fallback_files = [
            f["path"] for f in all_files
            if any(f["path"].endswith(ext) for ext in fallback_extensions)
        ][:5]
    
    if fallback_files:
        high_value_files = fallback_files
        selection_method = "fallback"
        logger.info(f"Fallback selected {len(fallback_files)} files")

    if len(high_value_files) == 0:
        return{
            "statusCode": 400,
            "body": {"error_code": "NO_ANALYZABLE_FILES"}
        }

    # ============================================
    # STEP 7: Fetch File Contents
    # ============================================
    file_contents = {}

    for file_path in high_value_files:
        content_response = get_file_content(owner=owner, repo=repo, file_path=file_path)

        if content_response["statusCode"] == 200:
            data = content_response["body"]["data"]
            if not data.get("skipped"):
                file_contents[file_path] = data["content"]
                logger.info(f"Fetched: {file_path} ({data['size']} bytes)")
            else:
                logger.info(f"Skipped: {file_path} ({data.get('reason')})")
        else:
            logger.warning(f"Failed to fetch: {file_path}")
        
    logger.info(f"Fetched content for {len(file_contents)} files")

    if len(file_contents) == 0:
        return {
            "statusCode": 400,
            "body": {"error_code": "NO_FILE_CONTENT_FETCHED"}
        }

    # ============================================
    # STEP 8: Generate Suggestions with Gemini
    # ============================================
    file_tree_paths = [f["path"] for f in all_files]

    gemini_response = generate_suggestions(
        metadata=metadata,
        file_tree=file_tree_paths,
        file_contents=file_contents
    )

    if gemini_response["statusCode"] != 200:
        return gemini_response

    suggestions = gemini_response["body"]["data"]["suggestions"]

    logger.info(f"Generated {len(suggestions)} video suggestions")

    # ============================================
    # STEP 9: Build Analysis Object
    # ============================================
    analysis = {
        "repo_name": metadata.get("name"),
        "description": metadata.get("description"),
        "language": metadata.get("language"),
        "stars": metadata.get("stars"),
        "topics": metadata.get("topics"),
        "html_url": metadata.get("html_url"),
        "default_branch": default_branch,
        "file_count": file_count,
        "files_analyzed": list(file_contents.keys()),
        "selection_method": selection_method
    }
    
    # ============================================
    # STEP 10: Save to Cache
    # ============================================
    if commit_sha:
        save_to_cache(github_url, commit_sha, analysis, suggestions)
    
    # ============================================
    # STEP 11: Return Results
    # ============================================
    return {
        "analysis": analysis,
        "suggestions": suggestions,
        "from_cache": False
    }
