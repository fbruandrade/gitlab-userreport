# GitLab Users Report Generator

This script connects to a GitLab instance using the python-gitlab library and generates reports of all users, billable users, and non-billable users.

## Requirements

- Python 3.6+
- python-gitlab
- pandas
- python-ldap (for Active Directory integration)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/Gitlab-UserReport.git
   cd Gitlab-UserReport
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the script with your GitLab API token:

```bash
python main.py --token YOUR_GITLAB_API_TOKEN
```

This will generate a CSV file with the current date in the filename (e.g., `gitlab_billable_users_2023-10-25.csv`).

### Programmatic Usage

You can also use the functions from the main script programmatically in your own Python code. See `example.py` for a demonstration:

```bash
python example.py
```

This example shows how to:
- Connect to GitLab
- Fetch billable users
- Generate a report
- Perform additional analysis on the report data using pandas

### Command Line Arguments

The script accepts the following command line arguments:

- `--url`: GitLab instance URL (default: https://gitlab.com or GITLAB_URL environment variable)
- `--token`: GitLab API token (default: GITLAB_TOKEN environment variable)
- `--output-all`: Output CSV file path for all users (default: gitlab_all_users_YYYY-MM-DD.csv)
- `--output-billable`: Output CSV file path for billable users (default: gitlab_billable_users_YYYY-MM-DD.csv)
- `--output-non-billable`: Output CSV file path for non-billable users (default: gitlab_non_billable_users_YYYY-MM-DD.csv)
- `--include-roles`: Include user roles in the reports
- `--max-role-only`: Include only the maximum role of each user (requires `--include-roles`)

Active Directory integration arguments:
- `--include-ad-info`: Include Active Directory information (manager and department) for billable users
- `--ad-server`: Active Directory server URL (default: AD_SERVER environment variable)
- `--ad-base-dn`: Base DN for LDAP search (default: AD_BASE_DN environment variable)
- `--ad-username`: Username for LDAP authentication (default: AD_USERNAME environment variable)
- `--ad-password`: Password for LDAP authentication (default: AD_PASSWORD environment variable)

### Examples

1. Connect to a self-hosted GitLab instance:
   ```bash
   python main.py --url https://gitlab.example.com --token YOUR_GITLAB_API_TOKEN
   ```

2. Specify custom output files:
   ```bash
   python main.py --token YOUR_GITLAB_API_TOKEN \
     --output-all all_users.csv \
     --output-billable billable_users.csv \
     --output-non-billable non_billable_users.csv
   ```

3. Include user roles in the reports:
   ```bash
   python main.py --token YOUR_GITLAB_API_TOKEN --include-roles
   ```

4. Include only the maximum role of each user:
   ```bash
   python main.py --token YOUR_GITLAB_API_TOKEN --include-roles --max-role-only
   ```

5. Using environment variables:
   ```bash
   export GITLAB_URL=https://gitlab.example.com
   export GITLAB_TOKEN=YOUR_GITLAB_API_TOKEN
   python main.py
   ```

6. Include Active Directory information for billable users:
   ```bash
   python main.py --token YOUR_GITLAB_API_TOKEN \
     --include-ad-info \
     --ad-server ldap://your-ad-server.com \
     --ad-base-dn "DC=example,DC=com" \
     --ad-username "CN=user,DC=example,DC=com" \
     --ad-password "your_password"
   ```

7. Using environment variables for Active Directory integration:
   ```bash
   export GITLAB_TOKEN=YOUR_GITLAB_API_TOKEN
   export AD_SERVER=ldap://your-ad-server.com
   export AD_BASE_DN="DC=example,DC=com"
   export AD_USERNAME="CN=user,DC=example,DC=com"
   export AD_PASSWORD="your_password"
   python main.py --include-ad-info
   ```

## Output

The script generates three CSV files:

1. **All Users Report**: Contains information about all GitLab users
2. **Billable Users Report**: Contains information about users who count toward your subscription seats
3. **Non-Billable Users Report**: Contains information about users who do not count toward your subscription seats

Each CSV file contains the following information for each user:

- id
- username
- name
- email
- state
- created_at
- last_activity_on
- is_admin
- external
- user_type (all, billable, or non_billable)

When the `--include-roles` argument is used, the following additional fields are included:

- max_role: The maximum role (highest access level) of the user across all projects and groups
- project_roles: A semicolon-separated list of project roles in the format "project_name (role_name)"
- group_roles: A semicolon-separated list of group roles in the format "group_name (role_name)"
- all_roles: A combined list of all project and group roles

When both `--include-roles` and `--max-role-only` arguments are used, only the `max_role` field is included, and the detailed project and group roles are omitted. This is useful for generating more concise reports when you only need to know the maximum role of each user.

When the `--include-ad-info` argument is used, the following additional fields are included for billable users:

- ad_manager: The name of the user's manager from Active Directory
- ad_department: The department/sector the user belongs to from Active Directory

## How Billable Users are Determined

In GitLab, billable users are those who count toward the number of subscription seats purchased in your subscription. The number of billable users changes when you block, deactivate, or add users to your instance during your current subscription period.

A user is **not** counted as a billable user if:

1. They are deactivated or blocked (state != 'active')
2. They are pending approval (state = 'blocked_pending_approval')
3. They are external users (external = True)
4. They are GitLab-created accounts:
   - Ghost User
   - Support Bot
   - Bot users for projects
   - Bot users for groups
   - Other internal users

Additional criteria that may apply in certain GitLab environments (not fully implemented in this script):
- They have only the Minimal Access role on GitLab Self-Managed Ultimate subscriptions
- They have only the Guest role on an Ultimate subscription
- They do not have project or group memberships on an Ultimate subscription

This script implements these criteria to categorize users as billable or non-billable.

## License

MIT
