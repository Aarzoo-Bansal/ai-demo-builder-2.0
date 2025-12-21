import requests
import boto3
from google import genai


def parse_github_url(github_url: str):
    """
    Extract owner and repo from the GitHub URL
    """



def handler(event, context):

    # get the github link
    github_url = event.get('github_url', None)

    if not github_url:
        return {"statusCode": 400,
                "body": "GitHub link is mandatory"
                }
    

    return {"statusCode": 200, "body": "Analysis Lambda"}
