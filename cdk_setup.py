import os
import shutil

import aws_cdk.aws_ecr_assets as ecra
import aws_cdk.aws_events as e
import aws_cdk.aws_events_targets as et
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_lambda_destinations as dest
import aws_cdk.aws_secretsmanager as sm
from aws_cdk import App, Stack, Duration, IgnoreMode
from constructs import Construct

output_directory = "./cdk.out"

if os.path.exists(output_directory):
    for f in os.listdir(output_directory):
        if os.path.isdir(f"{output_directory}/{f}") and f.startswith("asset."):
            shutil.rmtree(f"{output_directory}/{f}")


class RefrigeratorService(Construct):
    def __init__(self, scope: Construct, id: str):
        super().__init__(scope, id)
        stack = Stack(scope, "RefrigeratorCheckStack")
        eb = e.EventBus(stack, "RefrigeratorBus")
        d = dest.EventBridgeDestination(eb)
        code_img = ecra.DockerImageAsset(stack, "WyzeLambdaImage", directory=os.getcwd() + "/checker", exclude=[".git", ".gitignore", "cdk_out*", "cdk*", ".idea*", "venv*", __file__.split("/").pop()], ignore_mode=IgnoreMode.GIT)
        handler = lambda_.DockerImageFunction(stack,
                                              "lambdaContainerFunction",
                                              code=lambda_.DockerImageCode.from_ecr(repository=code_img.repository, tag=code_img.asset_hash),
                                              function_name="RefrigeratorChecker",
                                              memory_size=128,
                                              timeout=Duration.seconds(10),
                                              on_success=d,
                                              on_failure=d
                                              )
        twilio_secret_name = 'prod/twilio'
        wyze_secret_name = 'prod/wyze'
        handler.add_environment('WYZE_SECRET_NAME', wyze_secret_name)
        handler.add_environment('WYZE_DEVICE_NICKNAME', 'Refrigerator')
        handler.add_environment('EVENT_BUS_NAME', eb.event_bus_name)
        twilio_creds = sm.Secret.from_secret_name_v2(stack, "twilio_creds", twilio_secret_name)
        wyze_creds = sm.Secret.from_secret_name_v2(stack, "wyze_creds", wyze_secret_name)
        twilio_creds.grant_read(handler.role)
        wyze_creds.grant_read(handler.role)
        listen_handler_img = ecra.DockerImageAsset(stack, "OffListenerImage", directory=os.getcwd() + "/listener", exclude=[".git", ".gitignore", "cdk_out*", "cdk*", ".idea*", "venv*", __file__.split("/").pop()], ignore_mode=IgnoreMode.GIT)
        listen_handler = lambda_.DockerImageFunction(stack,
                                                     "lambdaContainerFunctionListener",
                                                     code=lambda_.DockerImageCode.from_ecr(repository=listen_handler_img.repository, tag=listen_handler_img.asset_hash),
                                                     function_name="RefrigeratorCheckerListener",
                                                     memory_size=128,
                                                     timeout=Duration.seconds(10),
                                                     on_success=d,
                                                     on_failure=d
                                                     )
        listen_handler.add_environment('TWILIO_BODY', 'Garage Fridge is not running.')
        listen_handler.add_environment('TWILIO_SECRET_NAME', twilio_secret_name)
        listen_handler.add_environment('WYZE_SECRET_NAME', wyze_secret_name)
        listen_handler.add_environment('WYZE_DEVICE_NICKNAME', 'Refrigerator')
        r = e.Rule(stack, "Every15MinutesRefrigerator", schedule=e.Schedule.rate(Duration.minutes(15)), targets=[et.LambdaFunction(handler)])
        r2 = e.Rule(stack, "OffEventListener", event_pattern=e.EventPattern(detail_type=["Refrigerator_status"]), event_bus=eb, targets=[et.LambdaFunction(listen_handler)])


app = App(outdir=output_directory)
RefrigeratorService(app, "RefrigeratorCheckService")
app.synth(validate_on_synthesis=True)
