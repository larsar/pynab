# Get token
# Download file
import datetime
import json
from os import environ

import requests

"""
To promote good security practice, this sample application gets credentials from
environment variables.
For convenience during development, it is sometimes preferrable to use a `.env`
file. To do so, copy the distributed file (`cp .env.dist .env`) and add your
credentials. If you use [Pipenv](https://docs.pipenv.org/), the .env file will
be loaded automatically. If not, you can use 
[python-dotenv](https://github.com/theskumar/python-dotenv):
1. Install the package by running `pip install python-dotenv`.
2. Uncomment the two lines below to load the environment variables in `.env`.
"""

# from dotenv import load_dotenv, find_dotenv
# load_dotenv(find_dotenv())

# This is your social security number. The same Id which is used when you log in with BankID.
CUSTOMERID = environ['CUSTOMERID']

# Get CLIENTID ('Applikasjonsnøkkel') and SECRET ('Passord') from https://secure.sbanken.no/Personal/ApiBeta/Info
CLIENTID = environ['CLIENTID']
SECRET = environ['SECRET']


def get_access_token(client_id, client_secret):
    data = {'grant_type': 'client_credentials'}
    r = requests.post('https://auth.sbanken.no/identityserver/connect/token', data,
                      auth=(CLIENTID, SECRET))
    return json.loads(r.content)['access_token']


def get_accounts(customer_id, access_token):
    headers = {'Authorization': 'Bearer {}'.format(access_token),
               'customerId': customer_id}
    r = requests.get('https://api.sbanken.no/exec.bank/api/v1/Accounts', headers=headers)
    return json.loads(r.content)['items']


def get_transactions(customer_id, access_token, account_id, start_date):
    headers = {'Authorization': 'Bearer {}'.format(access_token),
               'customerId': customer_id}
    params = {'startDate': start_date}
    r = requests.get('https://api.sbanken.no/exec.bank/api/v1/Transactions/{}'.format(account_id), headers=headers, params=params)
    return json.loads(r.content)['items']


def date_ago(minus_days):
    n = datetime.datetime.now()
    d = datetime.timedelta(days=minus_days)
    t = n - d
    return t.strftime("%Y.%m.%d")


def date_now():
    n = datetime.datetime.now()
    return n.strftime("%Y-%m-%d_%H%M%S")

def main():
    token = get_access_token(CLIENTID, SECRET)
    accounts = get_accounts(CUSTOMERID, token)
    ts = date_now()

    fa = open('data/{}-accounts.txt'.format(ts), 'w+')
    for account in accounts:
        fa.write('{}\n'.format(account))
        account_id = account['accountId']
        account_name = account['name']
        ft = open('data/{}-trans-{}.txt'.format(ts, account_name), 'w+')
        transactions = get_transactions(CUSTOMERID, token, account_id, date_ago(7))
        for transaction in transactions:
            ft.write('{}\n'.format(transaction))
        ft.close()
    fa.close()




    #print(date_now())

if __name__ == "__main__":
    main()
