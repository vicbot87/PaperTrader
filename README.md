***Written By Victor Botteicher

This application simulates option trades and is used to test option trading strategies in lieu of option trading paper accounts(because there are so few). This application uses a modestly aggressive tactic that will spend 25% of the user or users' total funds on each contract order. This application pulls real time option chain data from the wonderfully documented Tradier Brokerage's API. YOU MUST have a Tradier Brokerage Account in order to obtain an API key capable of providing real time data. This application is intended to be used with the TradingView website that triggers alerts to indicate when to buy and sell contracts via JSON webhooks. Input must be JSON format. NOTE: This application focuses on ITM and ATM contracts and will purchase the best At the Money contract from the given stock price and will "buy" contracts that expire on the Friday closest to the time of purchase.

THIS APPLICATION IS MEANT TO BE USED WITH SHORT TERM OPTION CONTRACT PURCHASES AND SELL TO CLOSES (STO). PAPERTRADER IS NOT TO BE USED FOR EXERCISING OPTIONS.
FAST TURNOVER ONLY!!! IF THE CONTRACTS ARE NOT SOLD By THEIR EXPIRATION DATE THEY WILL BE IN DATABASE LIMBO.

Setup: This is a Chalice application meant to be ran locally or in AWS Lambda. This application interfaces with two DynamoDb Databases that must be initialized before use. Initialization is possible using the first two "app.route()" methods within app.py. EXAMPLE: http://localhost:8000/initUserTable and http://localhost:8000/initContractTable . Once initialized you must insert your user or users using the "createPaperTraderUser" method.  EXAMPLE: http://localhost:8000/initUser/User123/Smith/50000 -> This completes database setup.

FOR FIRST TIME AWS USERS: In order to use Chalice and DynamoDb you must have an AWS account and have at least run 'aws config' to configure your local credentials. Whatever AWS account you choose to use must have access to both lambda and DynamoDb

Additional Setup: A tradier Api key must be optained from brokerage.tradier.com and placed set to the corresponding ACCESS_TOKEN value within the chalicelib/config.py file. Additionally in the same file, for security measures, you should set the SECRET_KEY value to a secret value you can pass via JSON to authenticate usage.

Usage: APPLICATTION MUST BE RUN USING PYTHON VENV. CHALICE WILL NOT WORK WITH A VENV. From the command line "chalice local" will create a local server to run the application. "chalice deploy" will run your application in AWS Lambda, and return a base URL to which you can issue commands. See below.


Required Packages: Python 3, Python venv, aws cli, chalice, pytz. --> most of these can be installed using pip/pip3/apt-get

To buy: JSON webhook posted to [YOUR_APPLICATION_URL]/longCallBuy

INPUT FORMAT:
{
    "stockPrice" : [CURRENT_STOCK_PRICE],
    "symbol" : "[STOCK_TICKER_SYMBOL]",
    "secretKey" : "[YOUR_SECRET_KEY]"
}

To sell all contracts of the given company owned by all users: JSON webhook posted to [YOUR_APPLICATION_URL]/longCallSell

INPUT FORMAT:
{
    "symbol" : "[STOCK_TICKER_SYMBOL]",
    "secretKey" : "[YOUR_SECRET_KEY]"
}

