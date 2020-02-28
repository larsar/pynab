import datetime
import json
import os
from collections import namedtuple

import requests
import yaml


class Ynab:
    def __init__(self):
        with open(r'config/ynab.yml') as file:
            config = yaml.full_load(file)
            self.access_token = config['access_token']
            self.budgets = None

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


class Sbanken:
    def __init__(self):
        with open(r'config/sbanken.yml') as file:
            config = yaml.full_load(file)
            self.client_id = config['client_id']
            self.client_secret = config['client_secret']
            self.customer_id = config['customer_id']
            self.accounts = None


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

        print(self.accounts)
        if str(account_number) not in self.accounts:
            print('Unknown account "{}"'.format(account_number))
            return None
        else:
            return self.accounts[str(account_number)]

    def account_transactions(self, account_id, start_date):
        headers = {'Authorization': 'Bearer {}'.format(self.access_token),
                   'customerId': self.customer_id}
        params = {'startDate': start_date}
        r = requests.get('https://api.sbanken.no/exec.bank/api/v1/Transactions/{}'.format(account_id), headers=headers,
                         params=params)
        return json.loads(r.content)['items']

    def date_ago(self, minus_days):
        n = datetime.datetime.now()
        d = datetime.timedelta(days=minus_days)
        t = n - d
        return t.strftime("%Y.%m.%d")

    def date_now(self):
        n = datetime.datetime.now()
        return n.strftime("%Y-%m-%d_%H%M%S")


ynab = Ynab()
sbanken = Sbanken()

for root, dirs, files in os.walk('config'):
    for budget_name in dirs:
        budget = ynab.budget(budget_name)
        ynab.budget_accounts(budget)
        with open(r'config/{}/config.yml'.format(budget_name)) as file:
            config = yaml.full_load(file)
            print(config)
            for bank in config['accounts']:
                print(bank)
                for account in config['accounts'][bank]:
                    #print(sbanken.account_transactions(account)
                    print(account)
                    print(sbanken.account(account))


