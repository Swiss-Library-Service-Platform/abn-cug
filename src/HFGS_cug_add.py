#####################################################################
# This script is used to add the CUG "BN_HFGS_Patron-HFGS" to users #
#####################################################################

# To use this script you need to install the almapiwrapper package:
# `pip install almapiwrapper`
#
# https://almapi-wrapper.readthedocs.io/en/latest/
#
# According to the documentation you also need to configure a `keys.json` file with the required API keys:
# - User management (R/W)
# - Configuration (R/W)
#
# The library fetches the API keys from the `keys.json` using the absolute path stored in environment
# variable `alma_api_keys`
#
# Installation documentation: https://almapi-wrapper.readthedocs.io/en/latest/getstarted.html
#
# The script needs `job_add_hfgs_cug.xml` to start the update job.
#
# The script uses `CUG_HFGS_updated.csv` to monitor the users to update.
# Required columns are:
#  - Name
#  - Vorname
#  - Geb.-Datum
#  - E-Mail
#  - primary_id
#  - updated
#  - skipped
#  - reason

# Import libraries
from almapiwrapper.users import fetch_users
from almapiwrapper.record import XmlData
from almapiwrapper.config import ItemizedSet, LogicalSet, NewItemizedSet, Job
from almapiwrapper.configlog import config_log

# Use to configure environment variable from script
# import os
# os.environ['alma_api_keys'] = '<path>/abn_keys.json'

import pandas as pd
import logging
from datetime import date, datetime
import time

# Config logs
config_log(f'hfgs_{str(date.today()).replace("-", "")}')


def strtodate(txt):
    return datetime.strptime(txt, '%Y-%m-%dZ')


new_user_group_code = 'ABN_HFGS_Patron-HFGS'
df = pd.read_csv('CUG_HFGS_updated.csv', index_col=False).fillna('')
print(df)

df['Geb.-Datum'] = pd.to_datetime(df['Geb.-Datum'])

# Iterate all users
for i, row in list(df.iterrows()):

    # Check if user is already updated
    if row['updated'] is True:
        logging.info(f'{i + 1} / {len(df)}: SKIPPED {row["E-Mail"]}')
        continue

    df.loc[i, 'reason'] = ''
    logging.info(f'{i + 1} / {len(df)}: handling {row["E-Mail"]}')

    # Fetch users by name
    users = [u for u in
             fetch_users(f'last_name~{row["Name"].replace(" ", "_")} and first_name~{row["Vorname"].replace(" ", "_")}',
                         zone='ABN')
             if u.primary_id.endswith('eduid.ch')]

    if len(users) == 0:
        logging.warning(f'No match found with name {row["Name"]}, {row["Vorname"]}')
        continue

    if len(users) > 1:
        logging.warning(f'Several accounts with same name: {", ".join([u.primary_id for u in users])}')

    # Filter by birthdate
    users_f = [u for u in users if row['Geb.-Datum'] == strtodate(u.data['birth_date'])]

    if len(users_f) > 1:
        logging.error(
            f'Several accounts with same name and same birth date ({row["Name"]}, {row["Vorname"]}), probably duplicated accounts => SKIPPED: {" ,".join([u.primary_id for u in users_f])}')
        df.loc[i, 'skipped'] = True
        df.loc[
            i, 'reason'] = f'Several accounts with same name and same birth date ({row["Name"]}, {row["Vorname"]}), probably duplicated accounts => SKIPPED: {", ".join([u.primary_id for u in users_f])}'
        df.to_csv('CUG_HFGS_updated.csv', index=False)
        continue

    if len(users_f) == 0:
        logging.warning(
            f'Match found with name {row["Name"]}, {row["Vorname"]}, but no match with birth date: looking for {row["Geb.-Datum"].strftime("%Y-%m-%d")} / found in alma accounts {", ".join([u.primary_id + " (" + u.data["birth_date"][:-1] + ")" for u in users])} => SKIPPED')
        df.loc[i, 'skipped'] = True
        df.loc[
            i, 'reason'] = f'Match found with name {row["Name"]}, {row["Vorname"]}, but no match with birth date: looking for {row["Geb.-Datum"].strftime("%Y-%m-%d")} / found in alma accounts {", ".join([u.primary_id + " (" + u.data["birth_date"][:-1] + ")" for u in users])} => SKIPPED'
        df.to_csv('CUG_HFGS_updated.csv', index=False)
        continue

    # Only one match found: handle account
    user_abn = users_f[0]
    primary_id = user_abn.primary_id
    df.loc[i, 'primary_id'] = primary_id
    df.to_csv('CUG_HFGS_updated.csv', index=False)

    if user_abn.data['user_group']['value'] == new_user_group_code:
        logging.info(f'{user_abn.primary_id}: user group already "{new_user_group_code}"')

    if user_abn.error is False:
        df.loc[i, 'updated'] = True
        df.to_csv('CUG_HFGS_updated.csv', index=False)

df.to_csv('CUG_HFGS_updated.csv', index=False)

time.sleep(5)

# Fetch members of logical set in alma with all users already having the related CUG
# Be sure to check the set id.
alma_members = LogicalSet('987568010008281', 'ABN').get_members()

# Get primary ids and deduplicate the result
primary_ids = list(set([u.primary_id for u in alma_members]))

# Select users that should be updated and still don't have the CUG
d = df.loc[df['updated'] & ~df.primary_id.isin(primary_ids)]

# Get list of primary ids to update
primary_ids_to_update = d.primary_id.unique()

# Delete maybe existing set with same name
ItemizedSet(zone='ABN', name='SLSP_hfgs_users_set_temp').delete()

# Create the new set
s = NewItemizedSet(zone='ABN',
                   name='SLSP_hfgs_users_set_temp',
                   content='USER',
                   description='Set used to add hfgs user group',
                   members=primary_ids_to_update).create()

# Add the set_id information in the job description data
job_data = XmlData(filepath='./job_add_hfgs_cug.xml')
job_data.content.xpath('.//name[text()="set_id"]')[0].getparent().find('value').text = s.set_id

# Start job
j = Job('148', 'ABN', 'P')
result = j.run(job_data)
