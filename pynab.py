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

    def get_budget(self, name):
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

    def get_accounts(self, budget):
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
            self.budgets = None



ynab = Ynab()
sbanken = Sbanken()

for root, dirs, files in os.walk('config'):
    for budget_name in dirs:
        budget = ynab.get_budget(budget_name)
        #ynab.get_accounts(budget)
        with open(r'config/{}/config.yml'.format(budget_name)) as file:
            config = yaml.full_load(file)
            print(config)
