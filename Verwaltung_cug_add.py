#################################################################################
# This script is used to add the CUG "ABN_Patron-Kantonale-Verwaltung" to users #
#################################################################################


# To use this script you need to install the almapiwrapper package:
# `pip install almapiwrapper`
#
# https://almapi-wrapper.readthedocs.io/en/latest/
#
# According to the documentation you also need to configure a `keys.json` file with the required API keys:
# - User management (R/W)
# - Analytics (R)
#
# The library fetches the API keys from the `keys.json` using the absolute path stored in environment
# variable `alma_api_keys`
#
# Installation documentation: https://almapi-wrapper.readthedocs.io/en/latest/getstarted.html

# NOTE: this version needs to be updated in order to be able to send emails.

# import almapiwrapper
from almapiwrapper.users import User, NewUser, fetch_users, fetch_user_in_all_iz, Fee, Loan
from almapiwrapper.users import check_synchro, force_synchro
from almapiwrapper.inventory import IzBib, NzBib, Holding, Item
from almapiwrapper.record import JsonData, XmlData
from almapiwrapper.config import ItemizedSet, LogicalSet, NewLogicalSet, NewItemizedSet, Job, Reminder, fetch_reminders
from almapiwrapper.analytics import AnalyticsReport
from almapiwrapper.configlog import config_log
from almapiwrapper import ApiKeys

import io
import pandas as pd

# sendmail is a custom package
from sendmail import sendmail


# Config logs
config_log()


def convert_dataframe_to_email_files(df: pd.DataFrame) -> bytes:
    """
    Convert a pandas dataframe to an Excel file
    :param df: pandas dataframe
    :return: bytes
    """
    output = io.BytesIO()

    # Use the BytesIO object as the filehandle.
    writer = pd.ExcelWriter(output, engine='openpyxl')

    # Write the data frame to the BytesIO object.
    df.to_excel(writer, sheet_name='Sheet1', index=False)

    # Save the workbook to the BytesIO object.
    writer.close()
    return output.getvalue()


# Read Analytics report
# ---------------------

# A configured analytics read-only key is required
report = AnalyticsReport('/shared/Aargauer Kantonsbibliothek 41SLSP_ABN/Reports/SLSP_ABN_reports_on_request/CUG/'
                         'Users_with_ag_ch_email_and_not_user_group',
                         'ABN')
data = report.data

# Filter data, additional check, analytics report should already be filtered
filtered_data = data.loc[~data['User Group Code'].isin(['ABN_HFGS_Patron-HFGS', 'ABN_Patron-ABN-Mediothek',
                                                        'ABN_Patron-Kantonale-Verwaltung'])]
primary_ids = filtered_data['Primary Identifier'].tolist()

# Limit to 50 users => limit risk in case of problem with analytics report
primary_ids = primary_ids[:50]


# Update users
# ------------
for primary_id in primary_ids:

    # Fetch user data
    u = User(primary_id, 'ABN')

    # Define user group
    u.data['user_group']['value'] = 'ABN_Patron-Kantonale-Verwaltung'

    # Update user, override is required to update user group if there is already a user group change on the account
    u.update(override=['user_group'])


# Email report
# ------------

# WARNING: this section will not work. It uses a local emailing server and library

if len(filtered_data) > 0:
    # At least one user group updated
    message = f'NB users receiving new "ABN_Patron-Kantonale-Verwaltung" group: {len(data)}'
    sendmail('raphael.rey@slsp.ch',
             'PROCESS update "ABN_Patron-Kantonale-Verwaltung" CUG',
             message,
             'users_with_new_CUG.xlsx',
             convert_dataframe_to_email_files(data))
else:
    # No user group updated
    message = f'No new user with "ABN_Patron-Kantonale-Verwaltung" group'
    sendmail('raphael.rey@slsp.ch',
             'PROCESS update "ABN_Patron-Kantonale-Verwaltung" CUG',
             message)
