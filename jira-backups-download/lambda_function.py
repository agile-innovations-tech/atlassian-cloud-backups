# -----------------------------------------------------------------------------
# Author: Aaron Morris
# Website: https://www.agile-innovations.tech
# Version 1.0.0
# Date: 2025-07-03
#
# License:
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree or at:
# https://mit-license.org/
#
# Description:
# This script is intended to be used as an AWS Lambda function. It downloads the most
# recent backup file from a Jira Cloud site and uploads the backup to S3.
#
# Video Tutorial: https://youtu.be/0zMJCQZe3xw
#
# Prerequisites:
#
# 1) Configure a secret in AWS Secrets Manager to store your Atlassian API
#    credentials.
#
#    Use the following format for the secret key/value pairs:
#      - email: your-email@example.com
#      - api_token: your-jira-api-token
#
# 2) Configure a bucket in AWS S3 to store your Jira backup files.
#
# 3) Configure the following environment variables for your Lambda function:
#    SITE_NAME, CREDENTIALS_SECRET_NAME, CREDENTIALS_SECRET_REGION_NAME, S3_BUCKET_NAME
#
#    For example:
#      - SITE_NAME = "my-jira-site.atlassian.net"
#      - CREDENTIALS_SECRET_NAME = "atlassian/backups/credentials"
#      - CREDENTIALS_SECRET_REGION_NAME = "us-east-1"
#      - S3_BUCKET_NAME = "jira-backups"
# -----------------------------------------------------------------------------

import boto3
from datetime import datetime
import json
import os
import requests

def lambda_handler(event, context):
    credentials = get_credentials()
    site_name = get_site_name()

    # Step 1: Get the latest task ID
    task_id = get_task_id(credentials, site_name)

    # Step 2: Get the URL to download the backup
    download_url = get_download_url(credentials, site_name, task_id)
    
    # Step 3: Download the file
    backup_file = download_file(credentials, site_name, download_url)

    # Step 4: Upload to S3
    filename = upload_to_s3(backup_file)

    return {"status": "success", "filename": filename}


def get_credentials():
    # Load configuration settings from Secrets Manager
    secret = get_secret()

    # Read the credentials
    email = secret["email"]
    api_token = secret["api_token"]
    credentials = (email, api_token)

    return credentials


def get_secret():

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=os.environ['CREDENTIALS_SECRET_REGION_NAME'],
    )

    get_secret_value_response = client.get_secret_value(
        SecretId=os.environ['CREDENTIALS_SECRET_NAME']
    )

    secret = json.loads(get_secret_value_response['SecretString'])

    return secret


def get_site_name():
    return os.environ['SITE_NAME']


def get_task_id(credentials, site_name):
    print("Querying latest task ID...")
    # Note: This API is undocumented and unsupported by Atlassian.
    status_resp = requests.get(f"https://{site_name}/rest/backup/1/export/lastTaskId", auth=credentials)
    status_resp.raise_for_status()
    task_id = status_resp.text
    print(f"Task ID: {task_id}")
    return task_id


def get_download_url(credentials, site_name, task_id):
    print(f"Querying status of task ID {task_id}...")
    # Note: This API is undocumented and unsupported by Atlassian.
    status_resp = requests.get(f"https://{site_name}/rest/backup/1/export/getProgress?taskId={task_id}",
                               auth=credentials)
    status_resp.raise_for_status()
    status = status_resp.json()["status"]
    print(f"Task status: {status}")

    if status != "Success":
        raise RuntimeError("The latest backup is not finished or was not successful.")
        
    download_url = status_resp.json()["result"]
    print(f"Backup file available at URL: {download_url}")
    return download_url


def download_file(credentials, site_name, download_url):
    print(f"Downloading from: {download_url}")
    backup_file = requests.get(f"https://{site_name}/plugins/servlet/{download_url}", auth=credentials, stream=True)
    backup_file.raise_for_status()
    return backup_file.raw


def upload_to_s3(backup_file):
    filename = f"jira-backup-{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')}.zip"
    print(f"Uploading to S3: {filename}")
    s3 = boto3.client("s3")
    s3.upload_fileobj(
        backup_file,
        os.environ['S3_BUCKET_NAME'],
        filename)
    return filename
