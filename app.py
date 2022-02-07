import base64
import json
import os
from functools import cache

import boto3
from botocore.exceptions import ClientError
from twilio.rest import Client as TwilioClient
from wyze_sdk import Client as WyzeClient


@cache
def get_secret(secret_name, region_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        print(e)
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            return json.loads(get_secret_value_response['SecretString'])
        else:
            return base64.b64decode(get_secret_value_response['SecretBinary'])


def handler(e, ctx):
    device_nickname = os.environ["WYZE_DEVICE_NICKNAME"]
    wyze_secret_name = os.environ["WYZE_SECRET_NAME"]
    region = os.getenv("AWS_REGION", "us-east-1")
    wyze_secret = get_secret(wyze_secret_name, region)
    wyze_client = WyzeClient(email=wyze_secret['WYZE_USERNAME'], password=wyze_secret['WYZE_PASSWORD'])
    for dev in wyze_client.plugs.list():
        if dev.nickname == device_nickname:
            if not dev.is_online:
                sms_body = os.getenv("TWILIO_BODY", "Your device is not running.")
                twilio_secret_name = os.environ["TWILIO_SECRET_NAME"]
                twilio_data = get_secret(twilio_secret_name, region)
                account_sid = twilio_data["TWILIO_USERNAME"]
                auth_token = twilio_data["TWILIO_PASSWORD"]
                service_sid = twilio_data["TWILIO_SID"]
                target = twilio_data["TWILIO_TARGET"]
                twilio_client = TwilioClient(account_sid, auth_token)
                twilio_client.messages.create(
                    messaging_service_sid=service_sid,
                    body=sms_body,
                    to=target
                )
                print("Refrigerator is off!")

if __name__ == "__main__":
    handler("", "")
