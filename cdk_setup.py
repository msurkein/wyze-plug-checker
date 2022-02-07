import os

import aws_cdk.aws_ecr_assets as ecra
import aws_cdk.aws_events as e
import aws_cdk.aws_events_targets as et
import aws_cdk.aws_lambda as lambda_
from aws_cdk import App, Stack, Duration
from constructs import Construct


class RefrigeratorService(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        stack = Stack(scope, "RefrigeratorCheckStack")
        code_img = ecra.DockerImageAsset(stack, "WyzeLambdaImage", directory=os.getcwd(), exclude=[".git*", "cdk_out*", "cdk*", ".idea*", "venv*", __file__.split("/").pop()])
        handler = lambda_.DockerImageFunction(stack,
                                              "lambdaContainerFunction",
                                              code=lambda_.DockerImageCode.from_ecr(repository=code_img.repository, tag=code_img.asset_hash),
                                              function_name="RefrigeratorChecker"
                                              )
        handler.add_environment('TWILIO_BODY', 'Garage Fridge is not running.')
        handler.add_environment('TWILIO_SECRET_NAME', 'prod/twilio')
        handler.add_environment('WYSZE_SECRET_NAME', 'prod/wyze')
        handler.add_environment('WYZE_DEVICE_NICKNAME', 'Refrigerator')
        r = e.Rule(stack, "Every15MinutesRefrigerator", schedule=e.Schedule.rate(Duration.minutes(15)), targets=[et.LambdaFunction(handler)])


app = App(outdir="./cdk.out")
RefrigeratorService(app, "RefrigeratorCheckService")
app.synth(validate_on_synthesis=True)
