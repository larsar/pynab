import datetime
import hashlib
import json
import os
from collections import namedtuple


import requests
import yaml

auth_header = None


def date_ago(minus_days):
    n = datetime.datetime.now()
    d = datetime.timedelta(days=minus_days)
    return n - d


class Budget:
    def __init__(self, name, budget_data, ynab, sbanken):
        self.budget_data = budget_data
        self.cached_transactions = None
        self.bank_transactions = []
        self.ynab = ynab
        try:
            with open(r'config/{}/config.yml'.format(name)) as file:
                self.config = yaml.full_load(file)
                # print(config)
                for bank in self.config['accounts']:
                    for account in self.config['accounts'][bank]:
                        account_number = str(account)
                        account_transactions = sbanken.account_transactions(account_number)
                        for transaction in account_transactions:
                            # print(sbanken.pseudo_transaction_id(transaction))
                            # print(sbanken.transaction_data(account_number, transaction))
                            self.add_bank_transaction(bank, sbanken.transaction_data(account_number, transaction))
        except FileNotFoundError:
            pass

    def accounts(self):
        r = requests.get('https://api.youneedabudget.com/v1/budgets/{}/accounts'.format(self.budget_data.id),
                         headers=self.ynab.auth_header())
        print('Accounts in "{}":'.format(self.budget_data.name))
        for account in json.loads(r.content)['data']['accounts']:
            print('\t{}: {}'.format(account['name'], account['id']))

    def transactions(self):
        if not self.cached_transactions:
            self.cached_transactions = []
            params = {'startDate': date_ago(7)}
            r = requests.get('https://api.youneedabudget.com/v1/budgets/{}/transactions'.format(self.budget_data.id),
                             headers=self.ynab.auth_header(), params=params)
            for t in json.loads(r.content)['data']['transactions']:
                self.cached_transactions.append(namedtuple('YnabTransactionData', t.keys())(*t.values()))

        return self.cached_transactions

    def add_bank_transaction(self, bank, transaction):
        account_id = self.config['accounts'][bank][int(transaction['account_number'])]
        transaction.pop('account_number', None)
        transaction['account_id'] = account_id
        transaction['date'] = datetime.datetime.fromisoformat(transaction['date']).strftime("%Y-%m-%d")

        self.bank_transactions.append(transaction)
        print(transaction)
        print(self.transactions())

    def find_transaction(self, import_id):
        for transaction in self.transactions():
            if transaction.import_id == import_id:
                return transaction
        return None

    def sync_transactions(self):
        import_transactions = []
        for bank_transaction in self.bank_transactions:
            if not self.find_transaction(bank_transaction['import_id']):
                print("Insert transaction")
                import_transactions.append(bank_transaction)

        if len(import_transactions) > 0:
            data = {'transactions': import_transactions}

            r = requests.post('https://api.youneedabudget.com/v1/budgets/{}/transactions'.format(self.budget_data.id),
                              json=data, headers=self.ynab.auth_header())
            print(r.content)


class Ynab:
    def __init__(self):
        with open(r'config/ynab.yml') as file:
            self.config = yaml.full_load(file)
            self.access_token = self.config['access_token']
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
                self.budgets[budget_name] = Budget(budget_name, budget_data, self, sbanken)

        if name not in self.budgets:
            print('Budget "{}" must be created in YNAB'.format(name))
            return None
        else:
            return self.budgets[name]


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
                self.accounts[a['accountNumber']] = namedtuple('SbankenAccountData', a.keys())(*a.values())

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
                trans.append(namedtuple('SbankenTransactionData', t.keys())(*t.values()))
            self.transactions[account_number] = trans

        return self.transactions[account_number]

    def pseudo_transaction_id(self, transaction):
        pseudo_key_data = '{}{}{}{}'.format(transaction.accountingDate,
                                            transaction.amount,
                                            transaction.transactionTypeCode,
                                            transaction.text)
        return hashlib.md5(pseudo_key_data.encode('utf-8')).hexdigest()

    def transaction_data(self, account_number, transaction):
        if transaction.isReservation:
            cleared = 'uncleared'
        else:
            cleared = 'cleared'

        return {'account_number': account_number,
                'date': transaction.accountingDate,
                'amount': int(transaction.amount * 1000),
                'memo': transaction.text,
                'cleared': cleared,
                'import_id': self.pseudo_transaction_id(transaction)
                }


def main():
    ynab = Ynab()
    sbanken = Sbanken()

    for root, dirs, files in os.walk('config'):
        for budget_name in dirs:
            budget = ynab.budget(budget_name, sbanken)
            # print(budget.accounts())
            # print(ynab.budget_transactions(budget))
            budget.sync_transactions()


if __name__ == "__main__":
    main()
