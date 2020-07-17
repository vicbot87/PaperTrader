from chalice import Chalice
import boto3
import os
from datetime import datetime
from chalicelib import config
import requests
import json
from Contract import Contract
from tradeHelper import tradeHelper
from decimal import Decimal
from pytz import timezone

### A METHOD TO CHECK IF THE MARKET IS OPEN
def tradingHours(status):
    est = timezone('US/Eastern')
    timeUnformatted = datetime.now(est)
    timeFormatted = timeUnformatted.strftime("%H:%M:%S")
    #Assuming it takes ~two seconds for trade to process
    if(timeFormatted >= '09:00:00' and timeFormatted <= '16:29:58'):
        return True
    else:
        status = '403 Request Must be Sent During Trading Hours'
        return False

app = Chalice(app_name='PaperTrader')

### A ROUTE METHOD TO CREATE A TABLE TO STORE USERS
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

### A ROUTE METHOD TO CREATE A TABLE TO STORE OPTION CONTRACTS
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
            'FullAccountBalance': account_balance,
            'AvailableAccountBalance': account_balance,
            'TradesRemaining': 5,
            'Date': dateString,
            'Profit': 0,
            'TotalOrdersPurchased': 0
        }
    )
    return {'Status': 'OK'}


### A ROUTE METHOD MADE TO RECEIVE A JSON POST FROM TRADING
### FINDS CLOSEST AT THE MONEY CONTRACT
### ADDS CONTRACT TO CONTRACT TABLE FOR EACH USER
@app.route('/longCallBuy', methods=['POST'])
def optionBuy():
    status = None
    webhook_message = app.current_request.json_body
    if tradingHours(status) == True:
        statusOk = tradeHelper.checkStatusFormatAndAuthenticationBuy(webhook_message, status)
        if  statusOk == True:
    #make URL Request to get option chains for given security at current price
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
                    tradeHelper.findATMContractForPurchase(json_response, webhook_message['stockPrice'], 'call', contractList)
                    contractToPurchase = contractList[0]
                    contractToPurchase.strikePrice = Decimal(contractToPurchase.strikePrice)
    #'buy' contracts for every user listed in table and make appropriate calculations
                    tradeHelper.insertContractsToTable(contractToPurchase)
                    status = "200 OK"
                else:
                    status = "400 Bad Request Company Symbol Not Found"
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
    return {'Status': status}


@app.route('/longCallSell', methods=['POST'])
def optionSell():
    status = None
    webhook_message = app.current_request.json_body
    if tradingHours(status) == True:
        statusOk = tradeHelper.checkStatusFormatAndAuthenticationSell(webhook_message, status)
        if  statusOk == True:
        #make URL Request to get option chains for given security at current price
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
                    
                    reducedContractTupleList = []
    #Find all the contracts in contract table that are of the passed in company ticker symbol
                    fullContractTupleList = tradeHelper.getContracts(webhook_message['symbol'])
                    if fullContractTupleList != None:
                    
                        reducedContractTupleList.append(fullContractTupleList[0]['contract_symbol']) 
    #Take the full list of contract tuples and reduce them to only the contract symbols
    #So we can more easily find the corresponding contracts in our json_response
                        tradeHelper.reduceContractList(fullContractTupleList, reducedContractTupleList)
                        
                        contractList = []

                        for contractSymbol in reducedContractTupleList:
                            tradeHelper.findATMContractToSell(json_response, contractSymbol, 'call', contractList)

                        tradeHelper.updateAndDelete(contractList)

                        status = "200 OK"
                    else:
                        status = "400 Bad Request None of those companies exist in the database"
                else:
                    status = "400 Bad Request Company Symbol Not Found"
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
    return {'Status': status}