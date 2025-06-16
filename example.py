#!/usr/bin/env python3
"""
Example script demonstrating how to use the GitLab Users Report Generator
programmatically.
"""

import os
from main import connect_to_gitlab, get_users, generate_report, get_user_roles, get_ad_info

def main():
    # Set your GitLab URL and token
    # You can also use environment variables:
    # gitlab_url = os.environ.get('GITLAB_URL', 'https://gitlab.com')
    # gitlab_token = os.environ.get('GITLAB_TOKEN')
    gitlab_url = 'https://gitlab.com'
    gitlab_token = 'YOUR_GITLAB_API_TOKEN'  # Replace with your actual token

    # Connect to GitLab
    print(f"Connecting to GitLab instance at {gitlab_url}...")
    gl = connect_to_gitlab(gitlab_url, gitlab_token)

    # Get users
    print("Fetching users...")
    all_users, billable_users, non_billable_users = get_users(gl)
    print(f"Found {len(all_users)} total users")
    print(f"Found {len(billable_users)} billable users")
    print(f"Found {len(non_billable_users)} non-billable users")

    # Generate reports
    all_output_file = 'example_all_users.csv'
    billable_output_file = 'example_billable_users.csv'
    non_billable_output_file = 'example_non_billable_users.csv'

    print(f"Generating reports...")
    # Create a dictionary mapping user IDs to their types
    user_types = {}
    for user in billable_users:
        user_types[user.id] = "billable"
    for user in non_billable_users:
        user_types[user.id] = "non_billable"

    # Set include_roles to True to include user roles in the reports
    include_roles = True

    # First, generate reports with all roles
    print("Generating reports with all roles...")
    all_report_df = generate_report(all_users, gl, all_output_file, "all", user_types, include_roles, False)
    billable_report_df = generate_report(billable_users, gl, billable_output_file, "billable", None, include_roles, False)
    non_billable_report_df = generate_report(non_billable_users, gl, non_billable_output_file, "non_billable", None, include_roles, False)

    # Then, generate reports with only maximum roles
    print("Generating reports with only maximum roles...")
    max_role_only = True
    max_role_all_output_file = 'example_all_users_max_role.csv'
    max_role_billable_output_file = 'example_billable_users_max_role.csv'
    max_role_non_billable_output_file = 'example_non_billable_users_max_role.csv'

    max_role_all_report_df = generate_report(all_users, gl, max_role_all_output_file, "all", user_types, include_roles, max_role_only)
    max_role_billable_report_df = generate_report(billable_users, gl, max_role_billable_output_file, "billable", None, include_roles, max_role_only)
    max_role_non_billable_report_df = generate_report(non_billable_users, gl, max_role_non_billable_output_file, "non_billable", None, include_roles, max_role_only)

    # Example of generating reports with Active Directory information for billable users
    print("\nGenerating reports with Active Directory information for billable users...")
    include_ad_info = True

    # Set your Active Directory connection parameters
    ad_params = {
        'server': 'ldap://your-ad-server.com',  # Replace with your AD server
        'base_dn': 'DC=example,DC=com',         # Replace with your base DN
        'username': 'CN=user,DC=example,DC=com', # Replace with your AD username
        'password': 'your_password'              # Replace with your AD password
    }

    ad_billable_output_file = 'example_billable_users_with_ad_info.csv'

    # Generate report with AD information only for billable users
    ad_billable_report_df = generate_report(billable_users, gl, ad_billable_output_file, "billable", None, include_roles, max_role_only, include_ad_info, ad_params)

    print(f"Report with Active Directory information saved to {ad_billable_output_file}")

    # Example of directly querying AD for a specific user
    if len(billable_users) > 0:
        user = billable_users[0]  # Get the first billable user as an example
        print(f"\nQuerying Active Directory for user {user.username}...")

        ad_info = get_ad_info(
            user.username,
            ad_params['server'],
            ad_params['base_dn'],
            ad_params['username'],
            ad_params['password']
        )

        print(f"Manager: {ad_info['manager']}")
        print(f"Department: {ad_info['department']}")

    # Display the first few rows of each report
    print("\nAll Users Report Preview:")
    print(all_report_df.head())

    print("\nBillable Users Report Preview:")
    print(billable_report_df.head())

    print("\nNon-Billable Users Report Preview:")
    print(non_billable_report_df.head())

    # You can also perform additional analysis on the DataFrames
    print("\nAdditional Analysis:")
    print(f"Number of admin users (all): {all_report_df['is_admin'].sum()}")
    print(f"Number of admin users (billable): {billable_report_df['is_admin'].sum()}")
    print(f"Number of admin users (non-billable): {non_billable_report_df['is_admin'].sum()}")

    # You can also filter the DataFrames further
    # For example, get users created in the last 30 days
    import pandas as pd
    from datetime import datetime, timedelta

    # Convert created_at to datetime for all reports
    all_report_df['created_at'] = pd.to_datetime(all_report_df['created_at'])
    billable_report_df['created_at'] = pd.to_datetime(billable_report_df['created_at'])
    non_billable_report_df['created_at'] = pd.to_datetime(non_billable_report_df['created_at'])

    # Filter for users created in the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_all_users = all_report_df[all_report_df['created_at'] > thirty_days_ago]
    recent_billable_users = billable_report_df[billable_report_df['created_at'] > thirty_days_ago]
    recent_non_billable_users = non_billable_report_df[non_billable_report_df['created_at'] > thirty_days_ago]

    print(f"\nUsers created in the last 30 days:")
    print(f"All users: {len(recent_all_users)}")
    print(f"Billable users: {len(recent_billable_users)}")
    print(f"Non-billable users: {len(recent_non_billable_users)}")

    # Example of working with user roles
    if include_roles:
        print("\nUser Roles Analysis:")

        # Count users with project roles
        users_with_project_roles = all_report_df[all_report_df['project_roles'] != ''].shape[0]
        print(f"Users with project roles: {users_with_project_roles}")

        # Count users with group roles
        users_with_group_roles = all_report_df[all_report_df['group_roles'] != ''].shape[0]
        print(f"Users with group roles: {users_with_group_roles}")

        # Count users with any roles
        users_with_any_roles = all_report_df[all_report_df['all_roles'] != ''].shape[0]
        print(f"Users with any roles: {users_with_any_roles}")

        # Example: Get roles for a specific user
        if len(all_users) > 0:
            user = all_users[0]  # Get the first user as an example
            print(f"\nRoles for user {user.username} (ID: {user.id}):")
            roles = get_user_roles(gl, user.id)

            print("Project roles:")
            for role in roles['project_roles']:
                print(f"  - {role['project_name']}: {role['role_name']}")

            print("Group roles:")
            for role in roles['group_roles']:
                print(f"  - {role['group_name']}: {role['role_name']}")

            print(f"Maximum role: {roles['max_role_name']}")

        # Analyze maximum roles
        print("\nMaximum Role Analysis:")

        # Count users by maximum role
        role_counts = max_role_all_report_df['max_role'].value_counts()
        print("Users by maximum role:")
        for role, count in role_counts.items():
            print(f"  - {role}: {count}")

        # Find users with Owner role
        owners = max_role_all_report_df[max_role_all_report_df['max_role'] == 'Owner']
        print(f"\nNumber of users with Owner role: {len(owners)}")

        # Find users with Maintainer role
        maintainers = max_role_all_report_df[max_role_all_report_df['max_role'] == 'Maintainer']
        print(f"Number of users with Maintainer role: {len(maintainers)}")

        # Find users with Developer role
        developers = max_role_all_report_df[max_role_all_report_df['max_role'] == 'Developer']
        print(f"Number of users with Developer role: {len(developers)}")

        # Find users with Reporter role
        reporters = max_role_all_report_df[max_role_all_report_df['max_role'] == 'Reporter']
        print(f"Number of users with Reporter role: {len(reporters)}")

        # Find users with Guest role
        guests = max_role_all_report_df[max_role_all_report_df['max_role'] == 'Guest']
        print(f"Number of users with Guest role: {len(guests)}")

        # Find users with no role
        no_role = max_role_all_report_df[max_role_all_report_df['max_role'] == '']
        print(f"Number of users with no role: {len(no_role)}")

    print("\nDone!")

if __name__ == "__main__":
    main()
