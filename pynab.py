import datetime
import hashlib
import json
import os
from collections import namedtuple

import requests
import yaml


def date_ago(minus_days):
    n = datetime.datetime.now()
    d = datetime.timedelta(days=minus_days)
    return n - d


class Ynab:
    def __init__(self):
        with open(r'config/ynab.yml') as file:
            config = yaml.full_load(file)
            self.access_token = config['access_token']
            self.budgets = None
            self.transactions = {}

    def auth_header(self):
        return {'Authorization': 'Bearer {}'.format(self.access_token)}

    def budget(self, name):
        if not self.budgets:
            self.budgets = {}
            r = requests.get('https://api.youneedabudget.com/v1/budgets', headers=self.auth_header())
            print(r.headers['X-Rate-Limit'])
            for b in json.loads(r.content)['data']['budgets']:
                self.budgets[b['name']] = namedtuple('Budget', b.keys())(*b.values())

        if name not in self.budgets:
            print('Budget "{}" must be created in YNAB'.format(budget_name))
            return None
        else:
            return self.budgets[name]

    def budget_accounts(self, budget):
        r = requests.get('https://api.youneedabudget.com/v1/budgets/{}/accounts'.format(budget.id),
                         headers=self.auth_header())
        print('Accounts in "{}":'.format(budget.name))
        for account in json.loads(r.content)['data']['accounts']:
            print('\t{}: {}'.format(account['name'], account['id']))

    def budget_transactions(self, budget):
        if budget.id not in self.transactions:
            trans = []
            params = {'startDate': date_ago(7)}
            r = requests.get('https://api.youneedabudget.com/v1/budgets/{}/transactions'.format(budget.id),
                             headers=self.auth_header(), params=params)
            for t in json.loads(r.content)['data']['transactions']:
                trans.append(namedtuple('YnabTransaction', t.keys())(*t.values()))
            self.transactions[budget.id] = trans

        return self.transactions[budget.id]


class Sbanken:
    def __init__(self):
        with open(r'config/sbanken.yml') as file:
            config = yaml.full_load(file)
            self.client_id = config['client_id']
            self.client_secret = config['client_secret']
            self.customer_id = config['customer_id']
            self.accounts = None
            self.transactions = {}

            r = requests.post('https://auth.sbanken.no/identityserver/connect/token',
                              {'grant_type': 'client_credentials'},
                              auth=(self.client_id, self.client_secret))
            self.access_token = json.loads(r.content)['access_token']

    def account(self, account_number):
        if not self.accounts:
            self.accounts = {}
            headers = {'Authorization': 'Bearer {}'.format(self.access_token),
                       'customerId': self.customer_id}
            r = requests.get('https://api.sbanken.no/exec.bank/api/v1/Accounts', headers=headers)
            for a in json.loads(r.content)['items']:
                self.accounts[a['accountNumber']] = namedtuple('SbankenAccount', a.keys())(*a.values())

        if account_number not in self.accounts:
            print('Unknown account "{}"'.format(account_number))
            return None
        else:
            return self.accounts[account_number]

    def account_transactions(self, account_number):
        if account_number not in self.transactions:
            trans = []
            headers = {'Authorization': 'Bearer {}'.format(self.access_token),
                       'customerId': self.customer_id}
            params = {'startDate': date_ago(7).strftime("%Y.%m.%d"), 'length': 1}
            r = requests.get('https://api.sbanken.no/exec.bank/api/v1/Transactions/{}'.format(
                self.account(account_number).accountId), headers=headers,
                params=params)
            for t in json.loads(r.content)['items']:
                trans.append(namedtuple('SbankenTransaction', t.keys())(*t.values()))
            self.transactions[account_number] = trans

        return self.transactions[account_number]

    def pseudo_transaction_id(self, transaction):
        print(transaction)
        print("foobar")
        pseudo_key_data = '{}{}{}{}'.format(transaction.accountingDate,
                                            transaction.amount,
                                            transaction.transactionTypeCode,
                                            transaction.text)

        return hashlib.md5(pseudo_key_data.encode('utf-8')).hexdigest()


ynab = Ynab()
sbanken = Sbanken()

for root, dirs, files in os.walk('config'):
    for budget_name in dirs:
        budget = ynab.budget(budget_name)
        ynab.budget_accounts(budget)
        # print(ynab.budget_transactions(budget))
        with open(r'config/{}/config.yml'.format(budget_name)) as file:
            config = yaml.full_load(file)
            print(config)
            for bank in config['accounts']:
                print(bank)
                for account in config['accounts'][bank]:
                    account_number = str(account)
                    account_transactions = sbanken.account_transactions(account_number)
                    for transaction in account_transactions:
                        print(sbanken.pseudo_transaction_id(transaction))
