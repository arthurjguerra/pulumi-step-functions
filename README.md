# Pulumi Step Functions

## Environment Setup
Create a Python virtual env:
```shell
pyenv install 3.10.4
pyenv virtualenv 3.10.4 pulumi-step-functions
pyenv activate pulumi-step-functions
```

Then, install the dependencies:
```shell
pip install -r requirements.txt
```

## Deployment
To deploy the infrastructure, run:
```shell
bash run
```

The script will create the lambda package, invoke Pulumi to create
the entire infrastructure and then clean up files from the package generation.

## What will be deployed?
Pulumi will create the following resources:
- 2 IAM Roles: the first will be used by the lambda function to push logs to CloudWatch, and the second
will be used by the step function
- Lambda function: function that prints a message in the output
- Step Function: function that will trigger Lambda based on a schedule
- Even Rule: (cron) schedule that will trigger the step function