"""
"""
import json
import logging

import pulumi
import yaml
import pulumi_aws as aws
from pulumi_aws.sfn import StateMachineLoggingConfigurationArgs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLUSTER_OPERATION_TYPE = [
    'update',
    'delete'
]


def create_lambda_iam_role():
    lambda_iam_role = aws.iam.Role(
        'pulumi-step-functions-lambda-role',
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }]
        }"""
   )

    aws.iam.RolePolicy(
        'pulumi-step-functions-lambda-role-policy',
        role=lambda_iam_role.id,
        policy="""{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                }
            ]
        }"""
    )

    return lambda_iam_role


def create_step_function_iam_role(lambda_function):
    """
    Create the IAM role with the required permissions for the step function to run
    :param lambda_function: Lambda function to be called by a step function
    :return: IAM role
    """
    sfn_iam_role = aws.iam.Role(
        'pulumi-step-functions-step-function-role',
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Service": "states.eu-west-1.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }]
        }"""
    )

    aws.iam.RolePolicy(
        'pulumi-step-functions-step-function-role-policy',
        role=sfn_iam_role.id,
        policy=lambda_function.arn.apply(lambda arn: """{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": "%s"
            }]
        }""" % arn)
    )

    return sfn_iam_role


def create_event_rule_iam_role(step_function):
    """
    Create an IAM role for the event rule to call a step function
    :param step_function: Step Function to allow the event rule to call
    :return: IAM role
    """
    rule_role = aws.iam.Role(
        'pulumi-step-functions-event-rule-role',
        name='pulumi-step-functions-event-rule-role',
        assume_role_policy="""{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Service": "states.eu-west-1.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }]
        }"""
    )

    aws.iam.RolePolicy(
        'pulumi-step-functions-event-rule-role-policy',
        name='pulumi-step-functions-event-rule-role-policy',
        role=rule_role.id,
        policy=step_function.arn.apply(lambda arn: """{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "states:StartExecution"
                ],
                "Resource": "%s"
            }]
        }""" % arn)
    )

    return rule_role


def create_event_rule(step_function, er_role):
    """
    Creates an event rule based on a defined schedule cron
    :param step_function: ARN of the step function to call
    :param er_role: IAM role of the event rule to call the step function
    """
    logging.info('Creating event rule...')

    rule = aws.cloudwatch.EventRule(
        name='pulumi-step-functions',
        resource_name='pulumi-step-functions-',
        description='Pulumi Step Functions',
        schedule_expression='30 10 ? * MON-FRI *',
        tags={
            'pulumi': True
        },
    )

    # adding target to the event rule
    target_input = {
        "pulumi_step_functions": True
    }

    aws.cloudwatch.EventTarget(
        resource_name='pulumi-step-functions',
        rule=rule.name,
        arn=step_function.arn,
        role_arn=er_role.arn,
        input=json.dumps(target_input)
    )

    # shows event rule name as an output
    pulumi.export('event_rule_{}_{}', rule.name)

    logging.info('Event rule created')


def create_step_function(lambda_function, step_function_role):
    """
    Creates the step function that will trigger a lambda function
    :param lambda_function: Lambda function to be called
    :param step_function_role: IAM role to grant permissions to the step function
    :return: state machine object
    """
    state_machine = aws.sfn.StateMachine(
        'pulumi-step-functions-step-function',
        name='pulumi-step-functions-step-function',
        role_arn=step_function_role.arn,
        definition=lambda_function.arn.apply(lambda arn: """{
          "Comment": "Example of a step function that calls lambda.",
          "StartAt": "first-step",
          "States": {
            "first-step": {
              "Type": "Task",
              "Resource": "arn:aws:states:::lambda:invoke",
              "OutputPath": "$.Payload",
              "Parameters": {
                "FunctionName": "%s",
                "Payload.$": "$"
              },
              "Retry": [
                {
                  "ErrorEquals": [
                    "Lambda.ServiceException",
                    "Lambda.AWSLambdaException",
                    "Lambda.SdkClientException"
                  ],
                  "IntervalSeconds": 2,
                  "MaxAttempts": 6,
                  "BackoffRate": 2
                }
              ],
              "End": true
            }
          },
          "TimeoutSeconds": 1800
        }""" % arn)
    )

    # shows step function name as an output
    pulumi.export('step_function', state_machine.id)

    return state_machine


def create_lambda_function(iam_role):
    """
    Creates an AWS lambda function to trigger travis from API
    :param iam_role: IAM role to grant permissions to Lambda
    :return: lambda function object
    """
    lambda_function = aws.lambda_.Function(
        'pulumi-step-functions-lambda',
        name='pulumi-step-functions-lambda',
        description='Lambda function',
        role=iam_role.arn,
        runtime="python3.9",
        handler="lambda_function.lambda_handler",
        code=pulumi.FileArchive("package.zip")
    )

    pulumi.export('lambda', lambda_function.name)

    return lambda_function


if __name__ == "__main__":
    logging.info('Deploying Lambda...')
    lambda_role = create_lambda_iam_role()
    lambda_fn = create_lambda_function(lambda_role)

    # Step Function depends on the Lambda function to exist
    logging.info('Deploying Step Function...')
    step_fn_role = create_step_function_iam_role(lambda_fn)
    step_fn = create_step_function(lambda_fn, step_fn_role)

    # The Event Rule depends on the Step Function to exist
    logging.info('Deploying event rule that will trigger the step function')
    event_rule_role = create_event_rule_iam_role(step_fn)
    create_event_rule(step_fn, event_rule_role)
