# pynab
Script for synchronizing transactions from Sbanken to YNAB. The script can sync multiple accounts and budgets.

**Note:** Please create a test budget in YNAB and test syncing transaction to it before syncing with your real budget.

## Prerequisites
* [Personal access token for YNAB](https://api.youneedabudget.com/#personal-access-tokens)
* [Sbanken API access](https://sbanken.no/bruke/utviklerportalen/)

## Software
The script can be run using Python 3. The simplest way to run it is using Docker.

## Sync mechanism
The basic configuration file does only need to know the name of the YNAB budget. Each account in YNAB,
that is going to receive transactions from Sbanken, need to have the Sbanken account number in the note field.
(11 digits, no spaces)

## Configuration
1. Create config from template: `cp config.template.yml config.yml`
2. Replace "<BUDGET NAME>" with the name of your budget in YNAB
3. Create env file from template: `cp .env_template .env`
4. Add your YNAB and Sbanken API credentials

**Note:** Newly created Sbanken API passwords might not work immediately.
If the sync script fails with a new password, then wait 20 minutes and try again.

## Running
Docker compose makes it easy to build a docker image, and run the sync job inside a container.
The script runs and then sleeps for a number of seconds. The sleep delay is specified in `docker-compose.yml`

### With Docker
`docer-compose up`

### Without Docker
1. Install python virtual environment: `make venv`
2. Install dependencies: `make install`
3. Run: `python3 pynab.py ./config.yml 86400`

## Automatic mapping
In Sbanken the transaction text/memo contains information that can be used to map the transaction to a payee. Payee
can then be automatically mapped to a category, based on the "categories" section in the configuration file.
```
*1997 19.06 Nok 131.64 Rema 1000 N
*1997 20.06 Usd 3.99 Amzn Digital*184Gf1o80 Kurs: 8.8622
*1997 21.06 Nok 179.00 Komplett.No Kurs
*1997 22.06 Nok 189.00 Spotify P2e5065bd1 Kurs
*1997 23.09 Nok 159.00 Netflix.Com Kurs: 1.0000
```

The script will only try to set payee and/or category for the YNAB transaction if it is not already set. In other words
you can override the configuration by updating the transaction manually in YNAB.

### Payees
Specify the payee names, as you would like to use in YNAB. The script will search for that name in the transaction's
text field. Optionally you can specify a list of search strings for the payee if the text does not contain the name
you want to use in your budget.

``` 
payees:
  'Apple':
  'Amazon':
    - 'AMZN Digital'
    - '<Some other text to find other Amazon transactions>'
```

### Categories
Specify each category in the "categories" section. Each category must have a list of payee names. Use the payee name as
they are defined in YNAB.

**Note:** The script will **not** create categories, only map transactions to existing categories. Make sure that the 
category name in the configuration file matches exactly the category name in YNAB.

``` 
categories:
  'Groceries':
    - 'Rema 1000'
    - 'Meny'
    - 'Kiwi'
  'Streaming':
    - 'Spotify'
    - 'Netflix'
```
