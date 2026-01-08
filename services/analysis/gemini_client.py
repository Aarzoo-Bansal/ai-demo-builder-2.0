# gemini_client.py
import os
import json
import boto3
import logging
from botocore.exceptions import ClientError
from google import genai

_gemini_api_key = None

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

def is_running_on_aws() -> bool:
    """
    Check if running on AWS Lambda
    """
    return "AWS_LAMBDA_RUNTIME_API" in os.environ


def get_api_key() -> str:
    """
    Get Gemini API key from AWS or environment (local)

    Returns:
        str: API key or None
    """

    global _gemini_api_key

    # if we already have the gemini key, return it
    if _gemini_api_key is not None:
        return _gemini_api_key
    
    if is_running_on_aws():
        logger.info("Running on the AWS instance. Fetching api key from AWS")
        api_key_param_name = os.environ.get("GEMINI_PARAM_NAME")

        if not api_key_param_name:
            logger.warning("Gemini Param Name is not defined")
            return None

        # Get token from AWS
        ssm_client = boto3.client("ssm")

        try:
            gemini_param_name = os.environ.get('GEMINI_PARAM_NAME')
            response = ssm_client.get_parameter(
                Name=gemini_param_name,
                WithDecryption=True
            )

            _gemini_api_key = response['Parameter']['Value']
        
        except ClientError as e:
            logger.error(f"Error fetching Gemini API Key: {e}")
            return None
    else:
        # if not running on AWS
        logger.info("Running Locally. Fetching api keys from environment")
        try:
            from dotenv import load_dotenv
            load_dotenv()
            _gemini_api_key = os.environ.get("GEMINI_API_KEY")
        except ImportError:
            logger.error(f"Unable to import loadenv")
            return None
    return _gemini_api_key


def build_prompt(metadata: dict, file_tree: dict, file_contents: dict) -> str:
    """
    Build the prompt for Gemini

    Args:
        metadata: repo metadata (name, description, language, etc.)
        file_tree: list of all file paths
        file_contents: dict of {path: content} for high-value files
    
    Returns:
        str: formatted prompt
    """
    # Format file tree (show first 100 files to save token)
    tree_str = "\n".join(file_tree[:100])
    if len(tree_str) > 100:
        tree_str += f"\n... and {len(file_tree) - 100} more files"

    # Format file contents
    contents_str = ""
    for path, content in file_contents.items():
        # Truncate very long files
        if len(content) > 5000:
            content = content[:5000] + "\n... (truncated)"

        # Detect language from extension
        ext = path.split('.')[-1] if '.' in path else ''
        contents_str += f"\n### {path}\n```{ext}\n{content}\n```\n"

    prompt = f"""You are analyzing a GitHub repository to suggest demo video clips for showcasing this project.


    ## Repository Information
    - **Name**: {metadata.get('name', 'Unknown')}
- **Description**: {metadata.get('description', 'No Description')}
- **Primary Language**: {metadata.get('language', 'Unknown')}
- **Stars**: {metadata.get('stars', 0)}
- **Topics**: {', '.join(metadata.get('topics', []))}

## Project Structure
```
{tree_str}
```

## Key Files Content
{contents_str}

## Your Task

Based on this repository analysis, suggest 3-5 demo video clips that would effectively showcase this project to potential users or employers.

For each clip, provide:
1. **title**: Short, descriptive title (e.g., "Project Introduction")
2. **duration_seconds**: Recommended length (30-120 seconds)
3. **description**: What to show/demonstrate in this clip
4. **talking_points**: Array of 3-5 key points to mention while recording
5. **features_to_highlight**: Specific features, code, or UI elements to demonstrate
6. **suggested_visuals**: What should appear on screen (code editor, terminal, browser, etc.)

Return your response as a valid JSON array only, with no additional text or markdown formatting:
[
    {{
        "title": "...",
        "duration_seconds": 60,
        "description": "...",
        "talking_points": ["...", "...", "..."],
        "features_to_highlight": ["...", "..."],
        "suggested_visuals": ["...", "..."]
    }}

]   

CRITICAL INSTRUCTIONS:
1. **Adapt to project type**- Don't give web app instructions for a CLI tool!
2. **Be ultra-specific**- Every command, every URL, every click should be spelled out
3. **Think chronologically**- Video 1 should set up context, later videos build on it
4. **Make it filmable**- Every instruction should be something that can be scren-recorded
5. **Include actual values**- Use realistic example data, URLs, commands
6. **Consider the viewer**- They might be seeing this for the first time
7. **Logical progression**- Each video should naturally lead to the next

Return ONLY valid JSON, nothing else"""
    
    return prompt


def generate_suggestions(metadata: dict, file_tree: list, file_contents: dict) -> dict:
    """
    Generate video suggestions using Gemini API

    Args:
        metadata: dict: repo metadata
        file_tree: list: list of all file paths
        file_contents: dict: dict of {path: content}

    Returns: 
        dict with statusCode and body containing suggestions or error
    """
    # Get API key
    api_key = get_api_key()

    if not api_key:
        return {
            "statusCode": 500,
            "body": {
                "error_code": "GEMINI_API_KEY_NOT_FOUND"
            }
        }
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Build Prompt
    prompt = build_prompt(metadata=metadata, file_tree=file_tree, file_contents=file_contents)

    try:
        # Generate response
        response = model.generate_content(prompt)
        response_text = response.text

        # Clean up response
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()

        suggestions = json.loads(response_text)

        return {
            "statusCode": 200, 
            "body": {
                "data": {
                    "suggestions": suggestions,
                    "suggestion_count": len(suggestions)
                }
            }
        }
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        return {
            "statusCode": 500, 
            "body": {"error_code": "GEMINI_RESPONSE_PARSE_ERROR"}
        }
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return {
            "statusCode": 500,
            "body": {"error_code": "GEMINI_API_ERROR", "message": str(e)}
        }


def select_important_files(files: list, max_files: int = 10) -> list:
    """
    Use Gemini to select important files from the tree

    Args:
        file_trees: list: list of {"path": "...", "size": ...} dicts
        max_files: int: maximum files to select

    Returns:
        list of file paths
    """
    api_key = get_api_key()
    if not api_key:
        return []
    
    file_tree = [f.get("path", "") for f in files if f.get("path")]
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    tree_str = "\n".join(file_tree[:500])
    if len(file_tree) > 500:
        tree_str += f"\n... and {len(file_tree) - 500} more files"

    prompt = f"""Analyze this file tree from a GitHub repository and select the {max_files} most important files for understanding the project.

    PRIORITIZE:
    1. Package manifests (package.json, requirements.txt, pyproject.toml, go.mod, etc.)
    2. README files
    3. Main entry points (index.js, main.py, app.js, App.tsx, etc.)
    4. API routes, controllers, handlers
    5. Core business logic and models

    SKIP:
    - Test files (.test.js, .spec.ts, _test.go)
    - Config files (unless critical like dockerfile)
    - Assets (images, fonts, css)
    - Lock files (package-lock.json, yarn.lock)
    - Build output (dist/, build/)
    - Dependencies (node_modules/, vendor/)

    FILE TREE:
    {tree_str}

Return only a JSON array of {max_files} file paths, nothing else:
["path/to/file1.js", "path/to/file2.py"]
"""
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean up markdown code blocks
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        files = json.loads(response_text)

        valid_files = [file for file in files if file in file_tree]

        return valid_files
    
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI file selection: {e}")
        return []
    except Exception as e:
        logger.error(f"AI file selection failed: {e}")
        return []