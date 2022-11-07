# pynab
Simple script for synchronizing transactions from Sbanken to YNAB. The script can sync
multiple accounts and budgets.

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

# Configuration
1. Create config from template: `cp config.template.yml config.yml`
2. Replace "<BUDGET NAME>" with the name of your budget in YNAB
3. Create env file from template: `cp .env_template .env`
4. Add your YNAB and Sbanken API credentials

**Note:** Newly created Sbanken API passwords might not work immediately.
If the sync script fails with a new password, then wait 20 minutes and try again.

# Running
Docker compose makes it easy to build a docker image, and run the sync job inside a container.
The script runs and then sleeps for a number of seconds. The sleep delay is specified in `docker-compose.yml`

## With Docker
`docer-compose up`

## Without Docker
1. Install python virtual environment: `make venv`
2. Install dependencies: `make install`
3. Run: `python3 pynab.py ./config.yml 86400`


