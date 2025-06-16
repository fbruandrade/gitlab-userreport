```python
#!/usr/bin/env python3
"""
GitLab Users Report Generator

This script connects to a GitLab instance using the python-gitlab library
and generates reports of all users, billable users, and non-billable users.
"""

import os
import sys
import argparse
import datetime
import time
import functools
import gitlab
import pandas as pd
import urllib3
import requests
import json
import pickle

import ldap


def retry_transient_errors(max_retries=3, delay=1, exceptions=(gitlab.exceptions.GitlabHttpError, gitlab.exceptions.GitlabConnectionError, requests.exceptions.Timeout)):
    """
    Decorator to retry functions that might fail due to transient GitLab API errors.

    Args:
        max_retries (int): Maximum number of retry attempts
        delay (int): Initial delay between retries in seconds (will be exponentially increased)
        exceptions (tuple): Tuple of exception classes to catch and retry on
                          - GitlabHttpError: HTTP errors from the GitLab API (including timeouts)
                          - GitlabConnectionError: Connection issues when communicating with GitLab

    Returns:
        function: Decorated function with retry logic
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay

            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        print(f"Maximum retries ({max_retries}) exceeded. Last error: {e}")
                        raise

                    print(f"Transient error occurred: {e}. Retrying in {current_delay} seconds... (Attempt {retries}/{max_retries})")
                    time.sleep(current_delay)
                    # Exponential backoff
                    current_delay *= 2

        return wrapper
    return decorator



@retry_transient_errors()
def connect_to_gitlab(url, token):
    """
    Connect to GitLab instance using the provided URL and token.

    Args:
        url (str): GitLab instance URL
        token (str): GitLab API token

    Returns:
        gitlab.Gitlab: GitLab connection object
    """
    try:
        gl = gitlab.Gitlab(url=url, private_token=token, ssl_verify=False)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        gl.auth()
        return gl
    except gitlab.exceptions.GitlabAuthenticationError:
        print("Authentication failed. Please check your token.")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to connect to GitLab: {e}")
        sys.exit(1)


@retry_transient_errors(max_retries=5, delay=3)
def get_user_roles_optimized(gl, user_id, skip_roles=False):
    """
    Get all roles for a specific user across all projects and groups.
    Optimized version that reduces API calls and handles errors gracefully.

    Args:
        gl (gitlab.Gitlab): GitLab connection object
        user_id (int): User ID
        skip_roles (bool): If True, skip detailed role analysis (for performance)

    Returns:
        dict: Dictionary with project and group roles, and maximum roles
    """
    roles = {
        'project_roles': [],
        'group_roles': [],
        'max_role_level': 0,
        'max_role_name': ''
    }

    if skip_roles:
        print(f"Skipping detailed role analysis for user {user_id} (performance mode)")
        return roles

    try:
        print(f"Getting roles for user {user_id}...")
        
        # Method 1: Try to get user directly and check memberships
        try:
            user = gl.users.get(user_id)
            print(f"Processing roles for user: {user.username}")
        except Exception as e:
            print(f"Warning: Could not get user {user_id}: {e}")
            return roles

        # Method 2: Use user memberships API if available (more efficient)
        try:
            # Try to get user's project memberships directly
            user_projects = user.projects.list(all=True)
            for project_membership in user_projects:
                try:
                    # Get the actual project to get the name
                    project = gl.projects.get(project_membership.id, lazy=True)
                    access_level = getattr(project_membership, 'access_level', 0)
                    
                    if access_level > roles['max_role_level']:
                        roles['max_role_level'] = access_level
                        roles['max_role_name'] = get_role_name(access_level)

                    roles['project_roles'].append({
                        'project_id': project_membership.id,
                        'project_name': getattr(project, 'name', f'Project-{project_membership.id}'),
                        'access_level': access_level,
                        'role_name': get_role_name(access_level)
                    })
                except Exception as e:
                    print(f"Warning: Error processing project membership {project_membership.id}: {e}")
                    continue

        except Exception as e:
            print(f"User memberships API not available or failed: {e}")
            # Fallback to the slower method but with optimizations
            return get_user_roles_fallback(gl, user_id)

        # Method 3: Get group memberships
        try:
            # Get user's groups using a more efficient approach
            page = 1
            per_page = 20
            groups_checked = 0
            max_groups_to_check = 500  # Limit to prevent timeout
            
            while groups_checked < max_groups_to_check:
                try:
                    groups_page = gl.groups.list(
                        page=page, 
                        per_page=per_page,
                        simple=True,
                        timeout=15
                    )
                    
                    if not groups_page:
                        break
                    
                    for group in groups_page:
                        groups_checked += 1
                        if groups_checked >= max_groups_to_check:
                            print(f"Reached maximum groups limit ({max_groups_to_check}) for user {user_id}")
                            break
                            
                        try:
                            # Check if user is member of this group
                            member = group.members.get(user_id, lazy=False)
                            if member:
                                access_level = getattr(member, 'access_level', 0)
                                
                                if access_level > roles['max_role_level']:
                                    roles['max_role_level'] = access_level
                                    roles['max_role_name'] = get_role_name(access_level)

                                roles['group_roles'].append({
                                    'group_id': group.id,
                                    'group_name': group.name,
                                    'access_level': access_level,
                                    'role_name': get_role_name(access_level)
                                })
                        except gitlab.exceptions.GitlabGetError:
                            # User is not a member of this group, which is normal
                            continue
                        except Exception as e:
                            print(f"Warning: Error checking group {group.id} for user {user_id}: {e}")
                            continue
                    
                    page += 1
                    time.sleep(0.2)  # Small delay between group pages
                    
                except Exception as e:
                    print(f"Error fetching groups page {page}: {e}")
                    break

        except Exception as e:
            print(f"Error getting group roles for user {user_id}: {e}")

    except Exception as e:
        print(f"Error getting roles for user {user_id}: {e}")

    print(f"Found {len(roles['project_roles'])} project roles and {len(roles['group_roles'])} group roles for user {user_id}")
    return roles


@retry_transient_errors(max_retries=3, delay=5)
def get_user_roles_fallback(gl, user_id):
    """
    Fallback method for getting user roles with heavy optimizations.
    Only checks a sample of projects to avoid timeouts.
    """
    print(f"Using fallback role detection for user {user_id}")
    
    roles = {
        'project_roles': [],
        'group_roles': [],
        'max_role_level': 0,
        'max_role_name': ''
    }

    try:
        # Only check first 100 projects (sample)
        projects_checked = 0
        max_projects_to_check = 100
        page = 1
        per_page = 20

        print(f"Checking sample of projects for user {user_id} roles...")
        
        while projects_checked < max_projects_to_check:
            try:
                projects_page = gl.projects.list(
                    page=page, 
                    per_page=per_page,
                    simple=True,
                    order_by='last_activity_at',  # Most active projects first
                    sort='desc',
                    timeout=10
                )
                
                if not projects_page:
                    break
                
                for project in projects_page:
                    projects_checked += 1
                    if projects_checked >= max_projects_to_check:
                        break
                    
                    try:
                        # Check if user is member
                        member = project.members.get(user_id, lazy=False)
                        if member:
                            access_level = getattr(member, 'access_level', 0)
                            
                            if access_level > roles['max_role_level']:
                                roles['max_role_level'] = access_level
                                roles['max_role_name'] = get_role_name(access_level)

                            roles['project_roles'].append({
                                'project_id': project.id,
                                'project_name': project.name,
                                'access_level': access_level,
                                'role_name': get_role_name(access_level)
                            })
                    except gitlab.exceptions.GitlabGetError:
                        # User is not a member, which is normal
                        continue
                    except Exception as e:
                        print(f"Warning: Error checking project {project.id}: {e}")
                        continue
                
                page += 1
                time.sleep(0.3)
                
            except Exception as e:
                print(f"Error in fallback project check page {page}: {e}")
                break

        print(f"Fallback method found {len(roles['project_roles'])} project roles for user {user_id}")

    except Exception as e:
        print(f"Error in fallback role detection for user {user_id}: {e}")

    return roles


@retry_transient_errors()
def get_user_roles(gl, user_id):
    """
    Get all roles for a specific user across all projects and groups.

    Args:
        gl (gitlab.Gitlab): GitLab connection object
        user_id (int): User ID

    Returns:
        dict: Dictionary with project and group roles, and maximum roles
    """
    roles = {
        'project_roles': [],
        'group_roles': [],
        'max_role_level': 0,
        'max_role_name': ''
    }

    try:
        # Get all projects
        projects = gl.projects.list(all=True)

        # For each project, check if the user is a member
        for project in projects:
            try:
                # Get project members
                members = project.members.list(all=True)

                # Check if the user is a member of this project
                for member in members:
                    if member.id == user_id:
                        # Update max role if this role is higher
                        if member.access_level > roles['max_role_level']:
                            roles['max_role_level'] = member.access_level
                            roles['max_role_name'] = get_role_name(member.access_level)

                        roles['project_roles'].append({
                            'project_id': project.id,
                            'project_name': project.name,
                            'access_level': member.access_level,
                            'role_name': get_role_name(member.access_level)
                        })
                        break
            except Exception as e:
                print(f"Error getting members for project {project.id}: {e}")

        # Get all groups
        groups = gl.groups.list(all=True)

        # For each group, check if the user is a member
        for group in groups:
            try:
                # Get group members
                members = group.members.list(all=True)

                # Check if the user is a member of this group
                for member in members:
                    if member.id == user_id:
                        # Update max role if this role is higher
                        if member.access_level > roles['max_role_level']:
                            roles['max_role_level'] = member.access_level
                            roles['max_role_name'] = get_role_name(member.access_level)

                        roles['group_roles'].append({
                            'group_id': group.id,
                            'group_name': group.name,
                            'access_level': member.access_level,
                            'role_name': get_role_name(member.access_level)
                        })
                        break
            except Exception as e:
                print(f"Error getting members for group {group.id}: {e}")

    except Exception as e:
        print(f"Error getting roles for user {user_id}: {e}")

    return roles

def get_role_name(access_level):
    """
    Convert GitLab access level to role name.

    Args:
        access_level (int): GitLab access level

    Returns:
        str: Role name
    """
    # GitLab access levels
    # 10 = Guest
    # 20 = Reporter
    # 30 = Developer
    # 40 = Maintainer
    # 50 = Owner

    access_level_map = {
        10: 'Guest',
        20: 'Reporter',
        30: 'Developer',
        40: 'Maintainer',
        50: 'Owner'
    }

    return access_level_map.get(access_level, f'Unknown ({access_level})')


def get_ad_info(username, ad_server, ad_base_dn, ad_username, ad_password):
    """
    Get Active Directory information for a user.

    Args:
        username (str): Username to search for in Active Directory
        ad_server (str): Active Directory server URL
        ad_base_dn (str): Base DN for LDAP search
        ad_username (str): Username for LDAP authentication
        ad_password (str): Password for LDAP authentication

    Returns:
        dict: Dictionary containing manager and department information
    """
    ad_info = {
        'manager': '',
        'department': ''
    }

    try:
        # Connect to Active Directory
        ldap_conn = ldap.initialize(ad_server)
        ldap_conn.protocol_version = ldap.VERSION3
        ldap_conn.set_option(ldap.OPT_REFERRALS, 0)

        # Bind with credentials
        ldap_conn.simple_bind_s(ad_username, ad_password)

        # Search for the user
        search_filter = f"(sAMAccountName={username})"
        attributes = ['manager', 'department']

        result = ldap_conn.search_s(ad_base_dn, ldap.SCOPE_SUBTREE, search_filter, attributes)

        # Process the result
        if result and len(result) > 0:
            dn, attrs = result[0]

            # Get manager
            if 'manager' in attrs:
                manager_dn = attrs['manager'][0].decode('utf-8')
                # Extract manager name from DN
                manager_cn = manager_dn.split(',')[0].split('=')[1]
                ad_info['manager'] = manager_cn

            # Get department
            if 'department' in attrs:
                ad_info['department'] = attrs['department'][0].decode('utf-8')

        # Unbind
        ldap_conn.unbind_s()

    except Exception as e:
        print(f"Error getting Active Directory information for user {username}: {e}")

    return ad_info

@retry_transient_errors(max_retries=10, delay=5)
def get_all_projects_with_checkpoints(gl, per_page=10, checkpoint_file='projects_checkpoint.json'):
    """
    Get all projects from GitLab with checkpoint system for recovery.
    
    Args:
        gl (gitlab.Gitlab): GitLab connection object
        per_page (int): Very small page size for stability
        checkpoint_file (str): File to save progress
    
    Returns:
        list: List of all projects
    """
    projects = []
    start_page = 1
    
    # Try to load checkpoint
    try:
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
            start_page = checkpoint_data.get('last_page', 1)
            print(f"Resuming from checkpoint - starting at page {start_page}")
    except FileNotFoundError:
        print("No checkpoint found, starting from page 1")
    except Exception as e:
        print(f"Error loading checkpoint: {e}, starting from page 1")
    
    page = start_page
    consecutive_empty_pages = 0
    max_consecutive_empty = 3  # Stop after 3 consecutive empty pages
    
    while consecutive_empty_pages < max_consecutive_empty:
        try:
            print(f"Fetching projects page {page} (per_page={per_page})...")
            
            # Use timeout and be more specific with parameters
            projects_page = gl.projects.list(
                page=page, 
                per_page=per_page, 
                order_by='id', 
                sort='asc',
                simple=True,  # Get simplified project data
                timeout=30    # 30 second timeout
            )
            
            if not projects_page:
                consecutive_empty_pages += 1
                print(f"Empty page {page} ({consecutive_empty_pages}/{max_consecutive_empty})")
                page += 1
                continue
            else:
                consecutive_empty_pages = 0  # Reset counter
            
            projects.extend(projects_page)
            print(f"Retrieved {len(projects)} projects so far... (page {page})")
            
            # Save checkpoint every 10 pages
            if page % 10 == 0:
                try:
                    checkpoint_data = {
                        'last_page': page + 1,
                        'total_projects': len(projects),
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                    with open(checkpoint_file, 'w') as f:
                        json.dump(checkpoint_data, f)
                    print(f"Checkpoint saved at page {page}")
                except Exception as e:
                    print(f"Warning: Could not save checkpoint: {e}")
            
            page += 1
            
            # Longer delay between requests for stability
            time.sleep(0.5)
            
            # Every 100 pages, take a longer break
            if page % 100 == 0:
                print(f"Taking a 10-second break after {page} pages...")
                time.sleep(10)
            
        except Exception as e:
            print(f"Error fetching projects page {page}: {e}")
            # Save emergency checkpoint
            try:
                emergency_checkpoint = {
                    'last_page': page,
                    'total_projects': len(projects),
                    'error': str(e),
                    'timestamp': datetime.datetime.now().isoformat()
                }
                with open(f'emergency_{checkpoint_file}', 'w') as f:
                    json.dump(emergency_checkpoint, f)
                print(f"Emergency checkpoint saved")
            except:
                pass
            raise
    
    # Clean up checkpoint file on successful completion
    try:
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            print("Checkpoint file cleaned up")
    except:
        pass
    
    print(f"Finished retrieving all projects. Total: {len(projects)}")
    return projects


@retry_transient_errors(max_retries=10, delay=5)
def get_all_groups_with_checkpoints(gl, per_page=10, checkpoint_file='groups_checkpoint.json'):
    """
    Get all groups from GitLab with checkpoint system for recovery.
    
    Args:
        gl (gitlab.Gitlab): GitLab connection object
        per_page (int): Very small page size for stability
        checkpoint_file (str): File to save progress
    
    Returns:
        list: List of all groups
    """
    groups = []
    start_page = 1
    
    # Try to load checkpoint
    try:
        with open(checkpoint_file, 'r') as f:
            checkpoint_data = json.load(f)
            start_page = checkpoint_data.get('last_page', 1)
            print(f"Resuming groups from checkpoint - starting at page {start_page}")
    except FileNotFoundError:
        print("No groups checkpoint found, starting from page 1")
    except Exception as e:
        print(f"Error loading groups checkpoint: {e}, starting from page 1")
    
    page = start_page
    consecutive_empty_pages = 0
    max_consecutive_empty = 3
    
    while consecutive_empty_pages < max_consecutive_empty:
        try:
            print(f"Fetching groups page {page} (per_page={per_page})...")
            
            groups_page = gl.groups.list(
                page=page, 
                per_page=per_page, 
                order_by='id', 
                sort='asc',
                simple=True,
                timeout=30
            )
            
            if not groups_page:
                consecutive_empty_pages += 1
                print(f"Empty groups page {page} ({consecutive_empty_pages}/{max_consecutive_empty})")
                page += 1
                continue
            else:
                consecutive_empty_pages = 0
            
            groups.extend(groups_page)
            print(f"Retrieved {len(groups)} groups so far... (page {page})")
            
            # Save checkpoint every 5 pages (groups usually fewer than projects)
            if page % 5 == 0:
                try:
                    checkpoint_data = {
                        'last_page': page + 1,
                        'total_groups': len(groups),
                        'timestamp': datetime.datetime.now().isoformat()
                    }
                    with open(checkpoint_file, 'w') as f:
                        json.dump(checkpoint_data, f)
                    print(f"Groups checkpoint saved at page {page}")
                except Exception as e:
                    print(f"Warning: Could not save groups checkpoint: {e}")
            
            page += 1
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching groups page {page}: {e}")
            # Save emergency checkpoint
            try:
                emergency_checkpoint = {
                    'last_page': page,
                    'total_groups': len(groups),
                    'error': str(e),
                    'timestamp': datetime.datetime.now().isoformat()
                }
                with open(f'emergency_{checkpoint_file}', 'w') as f:
                    json.dump(emergency_checkpoint, f)
                print(f"Emergency groups checkpoint saved")
            except:
                pass
            raise
    
    # Clean up checkpoint file
    try:
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            print("Groups checkpoint file cleaned up")
    except:
        pass
    
    print(f"Finished retrieving all groups. Total: {len(groups)}")
    return groups


@retry_transient_errors()
def get_users_with_batch_processing(gl):
    """
    Get all users from GitLab with batch processing for large instances.
    
    Args:
        gl (gitlab.Gitlab): GitLab connection object
    
    Returns:
        tuple: (all_users, billable_users, non_billable_users)
    """
    try:
        print("Starting user retrieval with batch processing...")
        
        # Get all users with smaller pages
        all_users = []
        page = 1
        per_page = 20  # Even smaller for users
        
        while True:
            try:
                print(f"Fetching users page {page}...")
                users_page = gl.users.list(
                    page=page, 
                    per_page=per_page, 
                    order_by='id', 
                    sort='asc',
                    timeout=30
                )
                
                if not users_page:
                    print(f"No more users found. Total users retrieved: {len(all_users)}")
                    break
                    
                all_users.extend(users_page)
                print(f"Retrieved {len(all_users)} users so far...")
                page += 1
                time.sleep(0.3)
                
            except Exception as e:
                print(f"Error fetching users page {page}: {e}")
                raise

        print(f"Finished retrieving all users. Total: {len(all_users)}")

        # Get projects and groups with checkpoint system
        print("Getting projects with checkpoint system...")
        projects = get_all_projects_with_checkpoints(gl, per_page=10)
        
        print("Getting groups with checkpoint system...")
        groups = get_all_groups_with_checkpoints(gl, per_page=10)

        # Process users in batches
        billable_users = []
        non_billable_users = []
        batch_size = 100
        
        for i in range(0, len(all_users), batch_size):
            batch_end = min(i + batch_size, len(all_users))
            print(f"Processing users batch {i//batch_size + 1}: users {i+1} to {batch_end}")
            
            batch_users = all_users[i:batch_end]
            
            for user in batch_users:
                # Check if user is non-billable based on criteria
                is_non_billable = False

                # 1. Deactivated or blocked users
                if user.state != 'active':
                    is_non_billable = True

                # 2. Pending approval users
                elif hasattr(user, 'state') and user.state == 'blocked_pending_approval':
                    is_non_billable = True

                # 3. External users
                elif user.external:
                    is_non_billable = True

                # 4. GitLab-created accounts (Ghost User, bots, etc.)
                elif (hasattr(user, 'username') and 
                      (user.username == 'ghost' or 
                       'bot' in user.username.lower() or 
                       user.username.startswith('support-'))):
                    is_non_billable = True

                # Add user to appropriate list
                if is_non_billable:
                    non_billable_users.append(user)
                else:
                    billable_users.append(user)
            
            # Short break between batches
            time.sleep(1)

        return all_users, billable_users, non_billable_users
        
    except Exception as e:
        print(f"Error in batch processing users: {e}")
        sys.exit(1)


# Update the main get_users function to use the new batch processing
@retry_transient_errors()
def get_users(gl):
    """
    Get all users from GitLab and determine their billable status.
    Uses batch processing for large instances.
    """
    return get_users_with_batch_processing(gl)


def generate_report_with_performance_mode(users, gl, output_file=None, user_type="all", user_types=None, include_roles=False, max_role_only=False, include_ad_info=False, ad_params=None, performance_mode=False):
    """
    Enhanced generate_report function with performance mode for large instances.
    
    Args:
        performance_mode (bool): If True, skip detailed role analysis for better performance
        ... (other args same as original)
    """
    # Extract relevant information from user objects
    user_data = []
    
    if include_roles and len(users) > 1000 and not performance_mode:
        print(f"Warning: {len(users)} users detected. Role analysis may take a very long time.")
        print("Consider using performance_mode=True to skip detailed role analysis.")
        response = input("Continue with full role analysis? (y/N): ").lower()
        if response != 'y':
            print("Skipping role analysis. Set include_roles=False or performance_mode=True")
            include_roles = False
    
    for i, user in enumerate(users):
        if i % 50 == 0:
            print(f"Processing user {i+1}/{len(users)}")
        
        # Determine user_type for this specific user
        current_user_type = user_type
        if user_types and user.id in user_types:
            current_user_type = user_types[user.id]

        user_info = {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'state': user.state,
            'created_at': user.created_at,
            'last_activity_on': user.last_activity_on,
            'is_admin': user.is_admin,
            'external': user.external,
            'user_type': current_user_type
        }

        # Get Active Directory information for billable users if requested
        if include_ad_info and (current_user_type == "billable") and ad_params:
            try:
                ad_info = get_ad_info(
                    user.username,
                    ad_params.get('server', ''),
                    ad_params.get('base_dn', ''),
                    ad_params.get('username', ''),
                    ad_params.get('password', '')
                )
                user_info['ad_manager'] = ad_info['manager']
                user_info['ad_department'] = ad_info['department']
            except Exception as e:
                print(f"Error getting AD info for user {user.username}: {e}")
                user_info['ad_manager'] = ''
                user_info['ad_department'] = ''

        # Get user roles if requested
        if include_roles:
            try:
                # Use optimized role detection
                roles = get_user_roles_optimized(gl, user.id, skip_roles=performance_mode)

                # Add maximum role
                user_info['max_role'] = roles['max_role_name']

                if not max_role_only:
                    # Add project roles
                    project_roles = []
                    for role in roles['project_roles']:
                        project_role = f"{role['project_name']} ({role['role_name']})"
                        project_roles.append(project_role)
                    user_info['project_roles'] = '; '.join(project_roles) if project_roles else ''

                    # Add group roles
                    group_roles = []
                    for role in roles['group_roles']:
                        group_role = f"{role['group_name']} ({role['role_name']})"
                        group_roles.append(group_role)
                    user_info['group_roles'] = '; '.join(group_roles) if group_roles else ''

                    # Add all roles combined
                    all_roles = project_roles + group_roles
                    user_info['all_roles'] = '; '.join(all_roles) if all_roles else ''

            except Exception as e:
                print(f"Error getting roles for user {user.id}: {e}")
                user_info['max_role'] = ''
                if not max_role_only:
                    user_info['project_roles'] = ''
                    user_info['group_roles'] = ''
                    user_info['all_roles'] = ''

        user_data.append(user_info)

    # Create DataFrame
    df = pd.DataFrame(user_data)

    # Save to CSV if output file is specified
    if output_file:
        df.to_csv(output_file, index=False)
        print(f"Report saved to {output_file}")

    return df


# Update the original generate_report to use the enhanced version
def generate_report(users, gl, output_file=None, user_type="all", user_types=None, include_roles=False, max_role_only=False, include_ad_info=False, ad_params=None):
    """
    Generate a report of users with automatic performance optimization.
    """
    # Automatically enable performance mode for large user sets with roles
    performance_mode = include_roles and len(users) > 500
    
    if performance_mode:
        print(f"Performance mode enabled due to {len(users)} users. Detailed role analysis will be limited.")
    
    return generate_report_with_performance_mode(
        users, gl, output_file, user_type, user_types, 
        include_roles, max_role_only, include_ad_info, ad_params, 
        performance_mode
    )


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(description='Generate reports of all GitLab users, billable users, and non-billable users')
    parser.add_argument('--url', default=os.environ.get('GITLAB_URL