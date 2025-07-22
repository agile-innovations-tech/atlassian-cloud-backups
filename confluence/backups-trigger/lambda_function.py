# -----------------------------------------------------------------------------
# Author: Aaron Morris
# Website: https://www.agile-innovations.tech
# Version 1.0.0
# Date: 2025-07-22
#
# License:
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree or at:
# https://mit-license.org/
# 
# Description:
# This script is intended to be used as an AWS Lambda function. It triggers the
# generation of a Confluence Cloud backup.
#
# TODO: Video Tutorial: TBD
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
# 2) Configure the following environment variables for your Lambda function:
#    SITE_NAME, CREDENTIALS_SECRET_NAME, CREDENTIALS_SECRET_REGION_NAME
#
#    For example:
#      - SITE_NAME = "my-confluence-site.atlassian.net"
#      - CREDENTIALS_SECRET_NAME = "atlassian/backups/credentials"
#      - CREDENTIALS_SECRET_REGION_NAME = "us-east-1"
# -----------------------------------------------------------------------------

import boto3
import json
import os
import requests

def lambda_handler(event, context):
    
    credentials = get_credentials()
    include_attachments = are_attachments_included(event)
    trigger_backup(credentials, include_attachments)

    return {"status": "success"}


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


def are_attachments_included(event):
    if "includeAttachments" in event and event["includeAttachments"]:
        return "true"

    return "false"


def trigger_backup(credentials, include_attachments):

    site_name = os.environ['SITE_NAME']

    print("Triggering Jira Cloud backup...")

    # Note: This API is undocumented and unsupported by Atlassian.
    response = requests.post(
        f"https://{site_name}/wiki/rest/obm/1.0/runbackup",
        auth=credentials,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
        data=f'{{"cbAttachments":"{include_attachments}", "exportToCloud":"true"}}'
    )

    response.raise_for_status()
