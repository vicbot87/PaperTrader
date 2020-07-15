import boto3
import os
import datetime
from chalicelib import config
import requests
import json
from Contract import Contract
from decimal import Decimal
from boto3.dynamodb.conditions import Key


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
    def findATMContractForPurchase(nested_dict, stockPrice, optionType, listOfContracts):
        for key, value in nested_dict.items():
            numElem = 0
            if type(value) is dict:
                tradeHelper.findATMContractForPurchase(value, stockPrice, optionType, listOfContracts)
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


    @staticmethod
    def findATMContractToSell(nested_dict, symbol, optionType, listOfContracts):
        for key, value in nested_dict.items():
            if type(value) is dict:
                tradeHelper.findATMContractToSell(value, symbol, optionType, listOfContracts)
            else:
                for i in range(len(value)):
                    if (value[i])['symbol'] == symbol and (value[i])['option_type'] == optionType and (value[i])['contract_size'] == 100:
                        contract = Contract((value[i])['symbol'], (value[i])['bid'], (value[i])['ask'],(value[i])['strike'], (value[i])['expiration_date'])
                        listOfContracts.append(contract)

##To Handle the case that the contracts to be purchase already exist in the database
    @staticmethod
    def getDuplicateContracts(user, contract):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderContractTable')
        numOfDuplicateContracts = 0
        currentPremiumPrice = -1
        try:
            response = table.get_item(
                Key={
                    'username': user['username'],
                    'contract_symbol': contract.symbol
                }
            )
            existingDuplicateContracts = response['Item']
            numOfDuplicateContracts = existingDuplicateContracts['NumberOfContracts']
            currentPremiumPrice = existingDuplicateContracts['AveragePremiumPrice']
        except:
            print('No duplicate contracts or Unable to fetch duplicates')
        return numOfDuplicateContracts, currentPremiumPrice

### A METHOD TO ADD THE PASSED CONTRACT TO THE CONTRACT TABLE
### INSERTS FOR EVERY USER
    @staticmethod
    def insertContractsToTable(contract):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderContractTable')
        users = tradeHelper.getUsers()
        for user in users:
            fullAccountBalance = Decimal(user['FullAccountBalance'])
            ExpendableFundsFloat = fullAccountBalance * Decimal(0.25)
            contractPrice = contract.premiumPrice() * 100
            amountOfContractsToPurchase = 0
            contractMultiplier = contractPrice
            numOfDuplicateContracts, currAveragePremiumPrice = tradeHelper.getDuplicateContracts(user, contract)

        ##Check Available Funds
            availableAccountBalance = Decimal(user['AvailableAccountBalance'])
        
            
            while ExpendableFundsFloat >= contractMultiplier and availableAccountBalance >= contractMultiplier:
                amountOfContractsToPurchase += 1
                contractMultiplier += contractPrice
            
            newPremiumPrice = contract.premiumPrice()
            #average out premium price if there are duplicate contracts
            if currAveragePremiumPrice != -1:
                newPremiumPrice = Decimal(((numOfDuplicateContracts * currAveragePremiumPrice) + (amountOfContractsToPurchase * contract.premiumPrice()))/(numOfDuplicateContracts + amountOfContractsToPurchase))

        ##Reduce Available Funds
            amountToWithdrawFromAccount = (contractMultiplier - contractPrice)
            tradeHelper.reduceAvailableAccountBalance(user, amountToWithdrawFromAccount)


            if amountOfContractsToPurchase > 0:
                table.put_item(
                    Item={
                        'username': user['username'],
                        'contract_symbol' : contract.symbol,
                        'AveragePremiumPrice' : newPremiumPrice,
                        'StrikePrice' : contract.strikePrice,
                        'ExpirationDate' : contract.expiration,
                        'NumberOfContracts' : (amountOfContractsToPurchase + numOfDuplicateContracts) 
                    }
                )
    
    @staticmethod
    def updateAndDelete(contractList):
        for contract in contractList:
            symbol = contract.symbol
            contractTuples = tradeHelper.getContracts(symbol)
            users = tradeHelper.getUsers()
            for cTuple in contractTuples:
                tradeHelper.updateAccountBalance(contract, cTuple, users)
                tradeHelper.deleteContract(cTuple)

    @staticmethod
    def updateAccountBalance(contract, cTuple, users):
        currPremium = contract.premiumPrice()
        diff = currPremium - cTuple['AveragePremiumPrice'] 
        numContracts = cTuple['NumberOfContracts']
        profitOrLoss = Decimal((diff*numContracts)*100)
        totalRefund = Decimal(((currPremium*numContracts)*100))
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderUserTable')
        for user in users:
            if user['username'] == cTuple['username']:
                try:
                    availableAccountBalance = Decimal(user['AvailableAccountBalance'])
                    updatedAvailableAccountBalance = (availableAccountBalance + totalRefund + profitOrLoss)
                    fullAccountBalance = Decimal(user['FullAccountBalance'])
                    updatedFullAccountBalance = (fullAccountBalance + profitOrLoss)
                    table.update_item(
                        Key={
                            'username': cTuple['username'],
                            'last_name' : user['last_name'] 
                        },
                        UpdateExpression='SET AvailableAccountBalance = :value1, FullAccountBalance = :value2',
                        ExpressionAttributeValues={
                        ':value1': updatedAvailableAccountBalance,
                        ':value2': updatedFullAccountBalance
                        }
                    )
                except Exception as e:
                    print('Unable to Update Account Balance')
                    print(e)
                    raise SystemExit(e)

    @staticmethod
    def deleteContract(cTuple):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderContractTable')
        try:
            response = table.delete_item(
                Key={
                    'username': cTuple['username'],
                    'contract_symbol': cTuple['contract_symbol']
                }
            )
        except Exception as e:
            print('Unable to Delete Contract Tuple from Contract Table')
            print(e)
            raise SystemExit(e)


    @staticmethod
    def reduceAvailableAccountBalance(user, amount):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderUserTable')
        try:
            existingOrdersPurchased = user['TotalOrdersPurchased']
            updatedOrdersPurchased = existingOrdersPurchased + 1
            availableAccountBalance = Decimal(user['AvailableAccountBalance'])
            updatedAvailableAccountBalance = (availableAccountBalance - amount)
            table.update_item(
                Key={
                    'username': user['username'],
                    'last_name' : user['last_name'] 
                },
                UpdateExpression='SET AvailableAccountBalance = :value1, TotalOrdersPurchased = :value2',
                ExpressionAttributeValues={
                ':value1': updatedAvailableAccountBalance,
                ':value2': updatedOrdersPurchased
                }
            )
        except Exception as e:
            print('Unable to Reduce Available account balance')
            print(e)
            raise SystemExit(e)

    @staticmethod
    def getAvailableAccountBalance(user):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderUserTable')
        availableAccountBalance = -1
        try:
            response = table.get_item(
                Key={
                    'username': user['username'],
                    'last_name': user['last_name']
                }
            )
            userAccount = response['Item']
            availableAccountBalance = userAccount['AvailableAccountBalance']
        except Exception as e:
            print('Available Account Balance Could not be Fetched')
            raise SystemExit(e)
        return availableAccountBalance

    @staticmethod
    def getUsers():
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderUserTable')
        scan_args = {
            'ProjectionExpression': "username, last_name, FullAccountBalance, AvailableAccountBalance, TradesRemaining, #Dt, Profit, TotalOrdersPurchased",
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


    @staticmethod
    def getSymbols(root_symbol):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderContractTable')
        scan_args = {
            'FilterExpression' : Key('contract_symbol').begins_with(root_symbol),
            'ProjectionExpression': "username, contract_symbol"
        }
        contracts = None
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = table.scan(**scan_args)
            contracts = response.get('Items')
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return contracts
    
    @staticmethod
    def getContracts(contractSymbol):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('PaperTraderContractTable')
        scan_args = {
            'FilterExpression' : Key('contract_symbol').eq(contractSymbol),
            'ProjectionExpression': "username, contract_symbol, AveragePremiumPrice, NumberOfContracts"
        }
        contracts = None
        done = False
        start_key = None
        while not done:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            response = table.scan(**scan_args)
            contracts = response.get('Items')
            start_key = response.get('LastEvaluatedKey', None)
            done = start_key is None
        return contracts


