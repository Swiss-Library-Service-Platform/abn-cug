#################################################################################
# This script is used to add the CUG "ABN_Patron-Kantonale-Verwaltung" to users #
#################################################################################

# MINIMAL VERSION

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


# import almapiwrapper
from almapiwrapper.users import User
from almapiwrapper.analytics import AnalyticsReport
from almapiwrapper.configlog import config_log

# Config logs
config_log()


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
