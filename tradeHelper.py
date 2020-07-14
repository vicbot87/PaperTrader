import boto3
import os
import datetime
from chalicelib import config
import requests
import json
from Contract import Contract
from decimal import Decimal

class tradeHelper():
### RETURNS CLOSEST FRIDAY WITH PROPER FORMATTING TO PASS TO TRADIER
### WHY? --> CONTRACTS END ON CLOSEST FRIDAY
    @staticmethod
    def getClosestFriday():
        today = datetime.date.today()
        friday = today + datetime.timedelta( (4-today.weekday()) % 7 )
        fridayDateString = friday.strftime("%Y-%m-%d")
        return fridayDateString

### FINDS CLOSEST AT THE MONEY CONTRACT
### TAKES IN JSON OPTION CHAIN DATA FROM TRADIER
### listOfContracts SHOULD BE PASSED AS AN EMPTY LIST
### listOfContracts WILL CONTAIN ONE CONTRACT UPON COMPLETTION
    @staticmethod
    def sortByStrikePrice(nested_dict, stockPrice, optionType, listOfContracts):
        for key, value in nested_dict.items():
            numElem = 0
            if type(value) is dict:
                tradeHelper.sortByStrikePrice(value, stockPrice, optionType, listOfContracts)
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

### TODO: CREATE A METHOD TO DETECT IF THAT CONTRACT ALREADY EXISTS IN TABLE AND IF IT DOES
### ADD TO THE AMOUNT OF CONTRACTS

### A METHOD TO ADD THE PASSED CONTRACT TO THE CONTRACT TABLE
### INSERTS FOR EVERY USER
    @staticmethod
    def insertContractsToTable(contract):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderContractTable')
        users = tradeHelper.getUsers()
        for user in users:
            accountBalance = Decimal(user['AccountBalance'])
            ExpendableFundsFloat = accountBalance * Decimal(0.25)
            contractPrice = contract.premiumPrice() * 100
            amountOfContractsToPurchase = 0
            contractMultiplier = contractPrice
            while ExpendableFundsFloat >= contractMultiplier:
                amountOfContractsToPurchase += 1
                contractMultiplier += contractPrice
            if amountOfContractsToPurchase > 0:
                table.put_item(
                    Item={
                        'username': user['username'],
                        'contract_symbol' : contract.symbol,
                        'PremiumPrice' : contract.premiumPrice(),
                        'StrikePrice' : contract.strikePrice,
                        'ExpirationDate' : contract.expiration,
                        'NumberOfContracts' : amountOfContractsToPurchase
                    }
                )

    @staticmethod
    def getUsers():
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderUserTable')
        scan_args = {
            'ProjectionExpression': "username, last_name, AccountBalance, TradesRemaining, #Dt, Profit, TotalTrades",
            'ExpressionAttributeNames': {"#Dt": "Date"}
        }
        users = None
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = table.scan(**scan_args)
            users = response.get('Items')
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return users


