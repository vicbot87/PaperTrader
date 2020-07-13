from chalice import Chalice
import boto3
import os
import datetime
from chalicelib import config
import requests
import json
from Contract import Contract

app = Chalice(app_name='PaperTrader')


def sortByStrikePrice(nested_dict, stockPrice, optionType, listOfContracts):
    for key, value in nested_dict.items():
        numElem = 0
        if type(value) is dict:
            sortByStrikePrice(value, stockPrice, optionType, listOfContracts)
        else:
            for i in range(len(value)):
                if (value[i])['strike'] <= stockPrice and (value[i])['option_type'] == optionType and (value[i])['contract_size'] == 100:
                    if numElem > 0:
                        if (value[i])['strike'] > listOfContracts[numElem-1].strikePrice:
                            contract = Contract((value[i])['symbol'], (value[i])['bid'], (value[i])['ask'],(value[i])['strike'], (value[i])['expiration_date'])
                            listOfContracts.pop()
                            listOfContracts.append(contract)
                    else:
                        contract = Contract((value[i])['symbol'], (value[i])['bid'], (value[i])['ask'],(value[i])['strike'], (value[i])['expiration_date'])
                        listOfContracts.append(contract)
                        numElem += 1

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
    print(json_response)
    contractList = []
    #sortByStrikePrice(json_response, 385, 'call', contractList)
    sortByStrikePrice(json_response, 385, 'call', contractList)
    contractToPurchase = contractList[0]
    print('\n')
    print('\n')
    print('CONTRACT TO PURCHASE \n')
    contractToPurchase.toString()
    print('\n')
    print('\n')
    
  
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

