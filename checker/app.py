import base64
import json
import os
import types
from functools import cache

import boto3
from botocore.exceptions import ClientError
from wyze_sdk import Client as WyzeClient


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
    wyze_secret_name = os.environ["WYZE_SECRET_NAME"]
    region = os.getenv("AWS_REGION", "us-east-1")
    wyze_secret = get_secret(wyze_secret_name, region)
    wyze_client = WyzeClient(email=wyze_secret['WYZE_USERNAME'], password=wyze_secret['WYZE_PASSWORD'])
    for dev in wyze_client.plugs.list():
        if dev.nickname == device_nickname:
            if dev.is_online:
                status = "On"
            else:
                status = "Off"
            detail_string = '"{}_status":"{}"'.format(device_nickname, status)
            event = {
                "Source": ctx.function_name,
                "Resources": [],
                "EventBusName": os.environ["EVENT_BUS_NAME"],
                "DetailType": "{}_status".format(device_nickname),
                "Detail": "{" + detail_string + "}"
            }
            ec = get_event_client(region)
            res = ec.put_events(Entries=[event])


if __name__ == "__main__":
    ctx_val = types.SimpleNamespace()
    ctx_val.function_name = "WyzeRefrigeratorClient"
    handler("", ctx_val)
