from chalice import Chalice
import boto3
import os
import datetime
from chalicelib import config
import requests
import json

#from chalicelib import db
app = Chalice(app_name='PaperTrader')

@app.route('/initUserTable')
def CreatePaperTraderUserTable():
    dynamodb = boto3.resource('dynamodb')
    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='PaperTraderUserTable',
        KeySchema=[
            {
                'AttributeName': 'username',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'last_name',
                'KeyType': 'RANGE'
            },
      
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'username',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'last_name',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
        'ReadCapacityUnits': 5,
        'WriteCapacityUnits': 5
        }
    )

# Wait until the table exists.
    table.meta.client.get_waiter('table_exists').wait(TableName='PaperTraderUserTable')

    return {'Status': 'OK'}

@app.route('/initUser/{username}/{last_name}')
def CreatePaperTraderUser(username,last_name):

    date = datetime.date.today()
    dateString = date.strftime("%Y-%m-%d")

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PaperTraderUserTable')
    table.put_item(
        Item={
            'username': username,
            'last_name': last_name,
            'AccountBalance': 1000,
            'TradesRemaining': 5,
            'Date': dateString,
            'Profit': 0,
            'TotalTrades': 0
        }
    )
    return {'Status': 'OK'}

@app.route('/test/{name}')
def testQueryParam(name):
    name = 'dingus '+name
    return {'Name': name}

@app.route('/optionChain')
def optionChain():

    url = '{}markets/options/chains'.format(config.API_BASE_URL)
    optionHeaders = {
        'Authorization': 'Bearer {}'.format(config.ACCESS_TOKEN),
        'Accept': 'application/json'
    }
    response = requests.get(url,
        params={'symbol': 'AAPL', 'expiration': '2020-07-17'},
        headers= optionHeaders
    )
    json_response = response.json()
    print(response.status_code)
    print(json_response)
    return {'Status': 'OK'}

@app.route('/restTest')
def restTest():

    url = '{}markets/quotes'.format(config.API_BASE_URL)
    headers = {
        'Authorization': 'Bearer {}'.format(config.ACCESS_TOKEN),
        'Accept': 'application/json'
    }
    response = requests.get(url,
        params={'symbols': 'AAPL'},
        headers= headers
    )
    print(response)
    json_response = response.json()
    print(response.status_code)
    print(json_response)
    return {'Status': 'OK'}

# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#
