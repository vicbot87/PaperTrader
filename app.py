from chalice import Chalice
import boto3
import os
import datetime
from chalicelib import config
import requests
import json
from Contract import Contract
from tradeHelper import tradeHelper
from decimal import Decimal

app = Chalice(app_name='PaperTrader')

### CREATE A TABLE TO STORE USERS
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

###CREATE A TABLE TO STORE OPTION CONTRACTS
@app.route('/initContractTable')
def CreatePaperTraderUserTable():
    dynamodb = boto3.resource('dynamodb')
    # Create the DynamoDB table.
    table = dynamodb.create_table(
        TableName='PaperTraderContractTable',
        KeySchema=[
            {
                'AttributeName': 'username',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'contract_symbol',
                'KeyType': 'RANGE'
            },
      
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'username',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'contract_symbol',
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

### A ROUTE METHOD TO ADD USERS TO THE USER TABLE
@app.route('/initUser/{username}/{last_name}/{account_balance}')
def CreatePaperTraderUser(username,last_name, account_balance):

    date = datetime.date.today()
    dateString = date.strftime("%Y-%m-%d")

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('PaperTraderUserTable')
    table.put_item(
        Item={
            'username': username,
            'last_name': last_name,
            'AccountBalance': account_balance,
            'TradesRemaining': 5,
            'Date': dateString,
            'Profit': 0,
            'TotalTrades': 0
        }
    )
    return {'Status': 'OK'}

@app.route('/test/{firstName}/{lastName}')
def testQueryParam(firstName,lastName):
    if firstName == 'von' or firstName == 'vic':
        fullName = 'dingus ' + firstName + ' ' + lastName
        return{'fullName': fullName}
    
    return {'error': 'ur name sucks, try again'}

### A ROUTE METHOD MADE TO RECEIVE A JSON POST FROM TRADING
### FINDS CLOSEST AT THE MONEY CONTRACT
### ADDS CONTRACT TO CONTRACT TABLE FOR EACH USER
@app.route('/longCall', methods=['POST'])
def optionChain():
    status = None
    webhook_message = app.current_request.json_body

    if ('stockPrice' in webhook_message and 'symbol' in webhook_message and 'secretKey' in webhook_message):
        properFormatting = True
    else:
        properFormatting = False

    if (properFormatting == True):
        if webhook_message['secretKey'] == config.SECRET_KEY:
    #make call to get option chains for given security at current price
            try:
                url = '{}markets/options/chains'.format(config.API_BASE_URL)
                optionHeaders = {
                    'Authorization': 'Bearer {}'.format(config.ACCESS_TOKEN),
                    'Accept': 'application/json'
                }
                response = requests.get(url,
                    params={'symbol': webhook_message['symbol'], 'expiration': tradeHelper.getClosestFriday()},
                    headers= optionHeaders
                )
    #receive option data
                json_response = response.json()
                if json_response['options'] != None: 
                    contractList = []

    #find At the Money(ATM) or closest In the Money(ITM) option contract
                    tradeHelper.sortByStrikePrice(json_response, webhook_message['stockPrice'], 'call', contractList)
                    contractToPurchase = contractList[0]
                    contractToPurchase.strikePrice = Decimal(contractToPurchase.strikePrice)
                    tradeHelper.insertContractsToTable(contractToPurchase)
                    status = "200 OK"
                else:
                    status = "400 Bad Request Company Symbol Not Found"
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
        else:
            status = "401 Incorrect Secret Key"
    else:
        status = "400 Bad Request"
  
    return {'Status': status}

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

def printUsers(Users):
    for User in Users:
        print(User['username'], " ",  User['last_name'])

