import os
import tempfile
import requests
import boto3
import json
import sys
from google.cloud import storage
from botocore.exceptions import NoCredentialsError
import base64

def lambda_handler(event, context):

    gcs_bucket_name = os.environ['bucketName']
    temp_dir = '/tmp'
    sns_message = json.loads(event['Records'][0]['Sns']['Message'])
    email = sns_message.get('email')
    assignment_id = sns_message.get('assignment_id')
    attempt = sns_message.get('attempt')
    submission_url = sns_message.get('submission_url')
    if is_valid_zip_url(submission_url):
        print(f"Received SNS message - for User: {email}, for Assignment: {assignment_id}")
        service_account_key = os.environ['GOOGLE_SERVICE_ACCOUNT_KEY']
        decodedKey = base64.b64decode(service_account_key)
        storage_client = storage.Client.from_service_account_info(json.loads(decodedKey))
        try:
            temp_download_dir = tempfile.mkdtemp(dir=temp_dir)  
            zip_file_path = os.path.join(temp_download_dir, 'release.zip')
            with requests.get(submission_url, stream=True) as response:
                with open(zip_file_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)

            path_in_bucket = f"{assignment_id}/{email}/attempt_{attempt}.zip"
            upload_to_gcs(zip_file_path, gcs_bucket_name,storage_client,path_in_bucket)
            send_email_ses("no-reply@dev.manicharanreddy.com",email,"Submission Status",f"Submission for assignment {assignment_id} downloaded and stored successfully in google bucket {gcs_bucket_name} at path {path_in_bucket}")#and stored successfully in google bucket "+gcs_bucket_name+" at path "+assignment_id+"/"+email+"/attempt_"+attempt+".zip")

        except Exception as e:
            print(f"Error: {e}")
            send_email_ses("no-reply@dev.manicharanreddy.com",email,"Submission Status",f"Could not download assignment due to the following error {e}, please re-submit")

        finally:
            print("Here in finally! Cleaning up the tempDirectory")
            cleanup_temp_dir(temp_download_dir)
    else:
        send_email_ses("no-reply@dev.manicharanreddy.com",email,"Submission Status","The submission failed due to invalid url, Please re-submit proper url")

def upload_to_gcs(source_path, bucket_name,storage_client, destination_blob_name):

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    print(f"uploading to bucket {bucket_name}")
    blob.upload_from_filename(source_path)

def send_email_ses(sender, recipient, subject, body):
    ses_client = boto3.client('ses', region_name='us-east-1')
    print(f"Sending email to {recipient} from {sender}")
    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}}
            }
        )
        print("Email sent! Message ID:", response['MessageId'],recipient)
    except NoCredentialsError:
        print("Credentials not available. Unable to send email.")

def is_valid_zip_url(url):
    try:
        response = requests.head(url,allow_redirects=True)
        content_type = response.headers['Content-Type']
        print(response.status_code,content_type)
        return response.status_code == 200 and 'zip' in content_type.lower()
    except Exception as e:
        print(f"Error checking URL validity: {e}")
        return False

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



