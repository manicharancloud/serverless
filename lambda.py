import os
import tempfile
import requests
import boto3
import json
import sys
from google.cloud import storage

def lambda_handler(event, context):
    # GitHub repository information
    github_repo = "manicharan/demozip" 
    github_token = "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"  

    # Google Cloud Storage information
    gcs_bucket_name = "testbucket1269"

    # AWS Lambda temporary directory
    temp_dir = '/tmp'

    try:
        # Create a temporary directory to store the downloaded release
        temp_download_dir = tempfile.mkdtemp(dir=temp_dir)

        # Get the URL for the latest code on the default branch
        zipball_url = f'https://github.com/{github_repo}/archive/refs/heads/main.zip'

        sns_message = json.loads(event['Records'][0]['Sns']['Message'])

        # Extract userid and email from the SNS message
        userid = sns_message.get('userid')
        email = sns_message.get('email')
        assignmentid = sns_message.get('assignmentid')

        # Your code here using userid and email
        print(f"Received SNS message - UserID: {userid}, Email: {email}, for Assignment: {assignmentid}")

        secrets_manager = boto3.client('secretsmanager', region_name='us-east-1')

        # Retrieve the secret value
        response = secrets_manager.get_secret_value(SecretId='GoogleCloudAccessKey')
        secret_content = json.loads(response['SecretString'])

        # Set Application Default Credentials using the service account key
        storage_client = storage.Client.from_service_account_info(secret_content)

        # Download the release ZIP file
        zip_file_path = os.path.join(temp_download_dir, 'release.zip')
        print(zip_file_path)
        with requests.get(zipball_url, stream=True) as response:
            with open(zip_file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

        # Upload the ZIP file to Google Cloud Storage

        upload_to_gcs(zip_file_path, gcs_bucket_name,storage_client, f"{assignmentid}/{userid}/submission.zip")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        print("Here in finally! Cleaning up the tempDirectory")
        # Clean up temporary directory
        cleanup_temp_dir(temp_download_dir)

def upload_to_gcs(source_path, bucket_name,storage_client, destination_blob_name):
    """Uploads a file to Google Cloud Storage."""
    # storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    print("uploading to bucket")

    # Upload the file
    blob.upload_from_filename(source_path)

def cleanup_temp_dir(temp_dir):
    """Clean up the temporary directory."""
    if os.path.exists(temp_dir):
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                os.remove(file_path)
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                os.rmdir(dir_path)
        os.rmdir(temp_dir)

# Uncomment to test locally

# # Read the event from standard input
# event_json = sys.stdin.read()

# # Parse the JSON content of the event
# event = json.loads(event_json)
# userid = event.get('userid')
# email = event.get('email')
# assignmentid = event.get('assignmentid')

# # Uncomment the following line for local testing
# lambda_handler(event, None)



