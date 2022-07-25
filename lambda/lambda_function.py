"""
Lambda function that prints a hello world message
"""


def print_msg(msg='Hello Pulumi'):
    """
    Prints a message in the output
    :param msg: message to print
    :return: None
    """
    print('This is the message: {}'.format(msg))


def lambda_handler(event, context):
    """
    AWS Lambda handler function
    :param event:
    :param context:
    :return: None
    """
    return print_msg('This is the Lambda Handler')


if __name__ == "__main__":
    print(print_msg('This is main'))
