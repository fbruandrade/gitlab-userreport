# GitLab Users and Topics Report Generator

This repository contains scripts to connect to a GitLab instance using the python-gitlab library and generate various reports:

1. **Users Report**: Generate reports of all users, billable users, and non-billable users.
2. **Topics Report**: Generate reports of all project topics, including counts of how many projects use each topic.

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

## Retry Mechanism for Transient Errors

The script includes a retry mechanism for handling transient errors that may occur during GitLab API calls. This makes the script more robust when dealing with network issues, rate limiting, or temporary service unavailability.

The following transient errors are automatically retried:
- GitlabHttpError: HTTP errors from the GitLab API
- GitlabConnectionError: Connection issues when communicating with GitLab
- GitlabTimeoutError: Timeouts when waiting for a response from GitLab

By default, the script will:
- Retry failed API calls up to 3 times
- Use exponential backoff between retries (starting at 1 second and doubling each time)
- Print informative messages about the errors and retry attempts

This retry mechanism is applied to the following functions:
- `connect_to_gitlab`: Initial connection to GitLab
- `get_user_roles`: Retrieving user roles across projects and groups
- `get_users`: Retrieving all users and determining their billable status

## Pagination for Large GitLab Instances

The script implements explicit pagination when retrieving users, projects, and groups from GitLab. This ensures that all data is properly retrieved even in large GitLab instances with thousands of users, projects, or groups.

Key features of the pagination implementation:
- Retrieves data in pages of 100 items at a time
- Continues fetching until all items are retrieved
- Displays progress information during retrieval
- Efficiently processes large datasets without memory issues

This makes the script suitable for use with GitLab instances of any size, from small teams to large enterprises with thousands of users.

## GitLab Topics Report Generator

The Topics Report Generator script (`topics_report.py`) analyzes all projects in a GitLab instance and generates reports about the topics used across these projects.

### Features

- Fetches all projects from a GitLab instance with efficient pagination
- Extracts and counts topics from each project
- Groups related topics (e.g., counts dotnet6 and dotnet8 as part of the dotnet group)
- Generates comprehensive reports in CSV format
- Handles large GitLab instances with thousands of projects
- Includes checkpoint system to resume from interruptions

### Basic Usage

Run the script with your GitLab API token:

```bash
python topics_report.py --token YOUR_GITLAB_API_TOKEN
```

This will generate three CSV files:
- `gitlab_topics_report_individual.csv`: Individual topics and their counts
- `gitlab_topics_report_grouped.csv`: Grouped topics and their counts
- `gitlab_topics_report_projects.csv`: Projects and their associated topics

### Programmatic Usage

You can also use the functions from the topics report script programmatically in your own Python code. See `example_topics.py` for a demonstration:

```bash
python example_topics.py
```

This example shows how to:
- Connect to GitLab
- Fetch all projects
- Analyze topics across projects
- Generate topic reports
- Perform additional analysis on the topics data

### Command Line Arguments

The script accepts the following command line arguments:

- `--url`: GitLab instance URL (default: GITLAB_URL environment variable)
- `--token`: GitLab API token (default: GITLAB_TOKEN environment variable)
- `--output`: Output file prefix for CSV reports (default: gitlab_topics_report)
- `--per-page`: Number of items per page for pagination (default: 10)

### Examples

1. Connect to a self-hosted GitLab instance:
   ```bash
   python topics_report.py --url https://gitlab.example.com --token YOUR_GITLAB_API_TOKEN
   ```

2. Specify a custom output file prefix:
   ```bash
   python topics_report.py --token YOUR_GITLAB_API_TOKEN --output my_topics_report
   ```

3. Using environment variables:
   ```bash
   export GITLAB_URL=https://gitlab.example.com
   export GITLAB_TOKEN=YOUR_GITLAB_API_TOKEN
   python topics_report.py
   ```

### Output

The script generates three CSV files:

1. **Individual Topics Report** (`*_individual.csv`):
   - `topic`: The name of the topic
   - `project_count`: The number of projects using this topic

2. **Grouped Topics Report** (`*_grouped.csv`):
   - `topic_group`: The base name of the topic group (e.g., "dotnet" for "dotnet6", "dotnet8")
   - `total_projects`: The total number of projects in this topic group

3. **Projects Topics Report** (`*_projects.csv`):
   - `project_id`: The ID of the project
   - `topics`: A comma-separated list of topics associated with the project
   - `topic_count`: The number of topics associated with the project

## License

MIT
