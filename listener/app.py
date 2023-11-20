import base64
import json
import os
import types
from functools import cache

import boto3
from botocore.exceptions import ClientError
from twilio.rest import Client as TwilioClient


@cache
def get_event_client(region_name):
    session = boto3.session.Session()
    event_client = session.client(service_name='events', region_name=region_name)
    return event_client


@cache
def get_secret_client(region_name):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    return client


@cache
def get_secret(secret_name, region_name):
    # Create a Secrets Manager client
    client = get_secret_client(region_name)

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
            res: dict = json.loads(get_secret_value_response['SecretString'])
            return res
        else:
            return base64.b64decode(get_secret_value_response['SecretBinary'])


def handler(e, ctx):
    device_nickname = os.environ["WYZE_DEVICE_NICKNAME"]
    print(e)
    if e["detail-type"] == f"{device_nickname}_status":
        if e["detail"][e["detail-type"]] == "off":
            print("Device is off, notifying...")
            sms_body = os.getenv("TWILIO_BODY", "Your device is not running.")
            twilio_secret_name = os.environ["TWILIO_SECRET_NAME"]
            region = os.getenv("AWS_REGION", "us-east-1")
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
        else:
            print("No need to notify")


if __name__ == "__main__":
    ctx_val = types.SimpleNamespace()
    ctx_val.function_name = "WyzeRefrigeratorClient"
    handler("", ctx_val)
