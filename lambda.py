import os
import tempfile
import requests
import boto3
import json
import sys
from google.cloud import storage

def lambda_handler(event, context):

    gcs_bucket_name = os.environ['bucketName']
    temp_dir = '/tmp'

    try:
        temp_download_dir = tempfile.mkdtemp(dir=temp_dir)

        sns_message = json.loads(event['Records'][0]['Sns']['Message'])
        userid = sns_message.get('userid')
        email = sns_message.get('email')
        assignmentid = sns_message.get('assignmentid')
        # submission_url = sns_message.get('submission_url')
        submission_url = "https://github.com/tparikh/myrepo/archive/refs/tags/v1.0.0.zip"

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
        with requests.get(submission_url, stream=True) as response:
            with open(zip_file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

        upload_to_gcs(zip_file_path, gcs_bucket_name,storage_client, f"{assignmentid}/{userid}/submission.zip")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        print("Here in finally! Cleaning up the tempDirectory")
        cleanup_temp_dir(temp_download_dir)

def upload_to_gcs(source_path, bucket_name,storage_client, destination_blob_name):

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    print("uploading to bucket")
    blob.upload_from_filename(source_path)

def cleanup_temp_dir(temp_dir):
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



