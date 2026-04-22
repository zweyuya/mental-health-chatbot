import json
import boto3
import urllib.request
import urllib.error
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

# --- Config (set these as Lambda env vars) ---
TABLE_NAME      = os.environ['DYNAMODB_TABLE']       # e.g. "conversations"
S3_BUCKET       = os.environ['S3_BUCKET']             # e.g. "my-pipeline-bucket"
GITHUB_TOKEN    = os.environ['GITHUB_TOKEN']          # Personal Access Token (repo scope)
GITHUB_OWNER    = os.environ['GITHUB_OWNER']          # e.g. "your-username"
GITHUB_REPO     = os.environ['GITHUB_REPO']           # e.g. "your-repo"
GITHUB_WORKFLOW = os.environ.get('GITHUB_WORKFLOW', 'deploy.yaml')


def lambda_handler(event, context):
    print("Lambda 3 triggered — starting export pipeline")

    # ── 1. Scan DynamoDB for all conversation records ──────────────────────────
    table = dynamodb.Table(TABLE_NAME)
    response = table.scan()
    items = response.get('Items', [])

    # Handle DynamoDB pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"Exported {len(items)} records from DynamoDB")

    # ── 2. Save as new_data.json to S3 ─────────────────────────────────────────
    payload = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "record_count": len(items),
        "conversations": items
    }

    s3.put_object(
        Bucket=S3_BUCKET,
        Key='new_data.json',
        Body=json.dumps(payload, default=str),
        ContentType='application/json'
    )
    print(f"Saved new_data.json to s3://{S3_BUCKET}/new_data.json")

    # ── 3. Trigger GitHub Actions workflow via repository_dispatch ─────────────
    github_url = (
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
        f"/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    )

    dispatch_body = json.dumps({
        "ref": "main",
        "inputs": {
            "record_count": str(len(items)),
            "s3_key": "new_data.json",
            "triggered_by": "lambda3-cloudwatch"
        }
    }).encode('utf-8')

    req = urllib.request.Request(
        github_url,
        data=dispatch_body,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28"
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as resp:
            print(f"GitHub Actions triggered — HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"GitHub API error {e.code}: {body}")
        raise

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Pipeline triggered",
            "records_exported": len(items),
            "s3_key": "new_data.json"
        })
    }
