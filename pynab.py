import datetime
import json
import os
import re
import sys
import time
import urllib.parse
from collections import namedtuple

import requests
import yaml

auth_header = None


def date_ago(minus_days):
    n = datetime.datetime.now()
    d = datetime.timedelta(days=minus_days)
    return n - d


class Budget:
    def __init__(self, budget_data, ynab, sbanken, config):
        self.budget_data = budget_data
        self.cached_transactions = None
        self.cached_categories = None
        self.cached_accounts = None
        self.bank_transactions = []
        self.ynab = ynab
        self.account_map = {}
        if budget_data.name in config:
            self.accounts()
            self.budget_config = config[budget_data.name] or {}
            self.account_map = self.accounts()
            for account_number in self.account_map:
                account_transactions = sbanken.account_transactions(account_number)
                for transaction in account_transactions:
                    self.add_bank_transaction(sbanken.transaction_data(account_number, transaction))

    def category_id(self, name):
        if not self.cached_categories:
            self.cached_categories = {}
            r = requests.get('https://api.youneedabudget.com/v1/budgets/{}/categories'.format(self.budget_data.id),
                             headers=self.ynab.auth_header())
            tree = json.loads(r.content)['data']
            for group in tree['category_groups']:
                for category in group['categories']:
                    if not category['hidden']:
                        self.cached_categories[category['name']] = category['id']

        return self.cached_categories.get(name, None)

    def accounts(self):
        if not self.cached_accounts:
            self.cached_accounts = {}
            r = requests.get('https://api.youneedabudget.com/v1/budgets/{}/accounts'.format(self.budget_data.id),
                             headers=self.ynab.auth_header())

            print('')
            print('YNAB accounts for {}:'.format(self.budget_data.name))
            print('*****************')
            for account in json.loads(r.content)['data']['accounts']:
                if account['note']:
                    self.cached_accounts[account['note']] = account['id']
                    print(
                        "{} ({}): balance={} cleared={} diff={}".format(account['name'],
                                                                        account['note'],
                                                                        int(account['balance'] / 1000),
                                                                        int(account['cleared_balance']) / 1000,
                                                                        int(account['uncleared_balance']) / 1000))
        return self.cached_accounts

    def transactions(self):
        if not self.cached_transactions:
            self.cached_transactions = []
            params = {'startDate': date_ago(int(os.getenv('YNAB_HISTORY_DAYS', default='30')))}
            r = requests.get('https://api.youneedabudget.com/v1/budgets/{}/transactions'.format(self.budget_data.id),
                             headers=self.ynab.auth_header(), params=params)
            for t in json.loads(r.content)['data']['transactions']:
                self.cached_transactions.append(namedtuple('YnabTransactionData', t.keys())(*t.values()))

        return self.cached_transactions

    def add_bank_transaction(self, transaction):
        account_id = self.account_map[transaction['account_number']]
        transaction.pop('account_number', None)
        transaction['account_id'] = account_id
        transaction['date'] = datetime.datetime.fromisoformat(transaction['date']).strftime("%Y-%m-%d")
        transaction['import_id'] = transaction['transaction_id']

        self.bank_transactions.append(transaction)

    def find_transaction(self, import_id):
        for transaction in self.transactions():
            if transaction.import_id == import_id:
                return transaction
        return None

    def transaction_with_payee(self, transaction):
        if 'payees' in self.budget_config:
            for payee in self.budget_config['payees'] or {}:
                match_list = [payee]
                if self.budget_config['payees'][payee]:
                    match_list.extend(self.budget_config['payees'][payee])
                for match in match_list:
                    if transaction['memo'] is None:
                        continue
                    p = re.compile(match, re.IGNORECASE)
                    m = p.search(transaction['memo'])
                    if m:
                        transaction['payee_name'] = payee
                        return self.transaction_with_category(transaction)

        return transaction

    def transaction_with_category(self, transaction):
        if 'payee_name' not in transaction:
            return transaction
        if self.budget_config['categories']:
            for category in self.budget_config['categories'] or {}:
                for payee in self.budget_config['categories'][category]:
                    if transaction['payee_name'] == payee:
                        transaction['category_id'] = self.category_id(category)
                        return transaction
        return transaction

    def sync_transactions(self):
        import_transactions = []
        update_transactions = []
        for bank_transaction in self.bank_transactions:
            if not self.find_transaction(bank_transaction['import_id']):
                t = self.transaction_with_payee(bank_transaction)
                t = self.transaction_with_category(t)
                import_transactions.append(t)

        for ynab_transaction in self.transactions():
            patch_transaction = ynab_transaction._asdict()
            patched = False

            if not ynab_transaction.payee_name:
                patch_transaction = self.transaction_with_payee(patch_transaction)
                if patch_transaction['payee_name']:
                    patched = True
            if not ynab_transaction.category_id:
                patch_transaction = self.transaction_with_category(patch_transaction)
                if patch_transaction['category_id']:
                    patched = True

            if patched:
                update_transactions.append(patch_transaction)

        if len(update_transactions) > 0:
            print('Patching {} transactions'.format(len(update_transactions)))
            data = {'transactions': update_transactions}
            r = requests.patch('https://api.youneedabudget.com/v1/budgets/{}/transactions'.format(self.budget_data.id),
                               json=data, headers=self.ynab.auth_header())

        if len(import_transactions) > 0:
            print('Inserting {} transactions'.format(len(import_transactions)))
            data = {'transactions': import_transactions}
            r = requests.post('https://api.youneedabudget.com/v1/budgets/{}/transactions'.format(self.budget_data.id),
                              json=data, headers=self.ynab.auth_header())


class Ynab:
    def __init__(self, access_token, budget_config):
        self.access_token = access_token
        self.budget_config = budget_config
        self.budgets = None

    def auth_header(self):
        return {'Authorization': 'Bearer {}'.format(self.access_token)}

    def budget(self, name, sbanken):
        if not self.budgets:
            self.budgets = {}
            r = requests.get('https://api.youneedabudget.com/v1/budgets', headers=self.auth_header())
            print(r.headers['X-Rate-Limit'])
            for b in json.loads(r.content)['data']['budgets']:
                budget_name = b['name']
                budget_data = namedtuple('BudgetData', b.keys())(*b.values())
                self.budgets[budget_name] = Budget(budget_data, self, sbanken, self.budget_config)

        if name not in self.budgets:
            print('Budget "{}" must be created in YNAB'.format(name))
            return None
        else:
            return self.budgets[name]


class Sbanken:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.accounts = None
        self.transactions = {}

        r = requests.post('https://auth.sbanken.no/identityserver/connect/token',
                          {'grant_type': 'client_credentials'},
                          auth=(urllib.parse.quote(self.client_id), urllib.parse.quote(self.client_secret)))
        self.access_token = json.loads(r.content)['access_token']

    def account(self, account_number):
        if not self.accounts:
            self.accounts = {}
            headers = {'Authorization': 'Bearer {}'.format(self.access_token)}
            r = requests.get('https://publicapi.sbanken.no/apibeta/api/v2/Accounts', headers=headers)
            print('')
            print('Sbanken accounts:')
            print('*****************')
            for a in json.loads(r.content)['items']:
                self.accounts[a['accountNumber']] = namedtuple('SbankenAccountData', a.keys())(*a.values())
                print(
                    "{} ({}): balance={} cleared={} diff={}".format(a['name'],
                                                                    a['accountNumber'],
                                                                    a['available'],
                                                                    a['balance'],
                                                                    a['available'] - a['balance']))

        if account_number not in self.accounts:
            print('Unknown account "{}"'.format(account_number))
            return None
        else:
            return self.accounts[account_number]

    def account_transactions(self, account_number):
        if account_number not in self.transactions:
            trans = []
            headers = {'Authorization': 'Bearer {}'.format(self.access_token)}
            params = {'startDate': date_ago(int(os.getenv('SBANKEN_HISTORY_DAYS', default='30'))).strftime("%Y.%m.%d"),
                      'length': 1000}

            r = requests.get('https://publicapi.sbanken.no/apibeta/api/v2/Transactions/archive/{}'.format(
                self.account(account_number).accountId), headers=headers,
                params=params)
            for t in json.loads(r.content)['items']:
                trans.append(namedtuple('SbankenTransactionData', t.keys())(*t.values()))
            self.transactions[account_number] = trans

        return self.transactions[account_number]

    def transaction_data(self, account_number, transaction):

        return {
            'transaction_id': transaction.transactionId,
            'account_number': account_number,
            'date': transaction.accountingDate,
            'amount': int(transaction.amount * 1000),
            'memo': transaction.text,
            'cleared': 'cleared',
            'approved': True
        }


def main(config_file):
    with open(config_file, 'r') as file:
        config = yaml.full_load(file)

    ynab = Ynab(os.getenv('YNAB_ACCESS_TOKEN'), config['budgets'])
    sbanken = Sbanken(os.getenv('SBANKEN_CLIENT_ID'), os.getenv('SBANKEN_CLIENT_SECRET'))

    for budget_name in config['budgets']:
        budget = ynab.budget(budget_name, sbanken)
        budget.sync_transactions()


if __name__ == "__main__":

    while (True):
        main(sys.argv[1])
        if len(sys.argv) == 3:
            print("Sleeping for {} seconds...".format(sys.argv[2]))
            time.sleep(int(sys.argv[2]))
        else:
            exit(0)
