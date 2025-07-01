#!/usr/bin/env python3
"""
Script to analyze GitLab project topics.

This script fetches all projects from a GitLab instance, extracts their topics,
and generates a report showing:
1. All topics and the number of projects using each topic
2. Grouped topics (e.g., all dotnet projects) and their counts
3. Total number of projects with topics

The script handles pagination for large GitLab instances with many projects.
"""

import os
import sys
import argparse
import datetime
import time
import pandas as pd
from collections import Counter, defaultdict

from main import connect_to_gitlab, get_all_projects_with_checkpoints, retry_transient_errors


@retry_transient_errors()
def get_project_topics(gl, project_id):
    """
    Get topics for a specific project.
    
    Args:
        gl (gitlab.Gitlab): GitLab connection object
        project_id (int): Project ID
        
    Returns:
        list: List of topics for the project
    """
    try:
        project = gl.projects.get(project_id)
        return project.topics
    except Exception as e:
        print(f"Error getting topics for project {project_id}: {e}")
        return []


def analyze_topics(projects, gl):
    """
    Analyze topics from all projects.
    
    Args:
        projects (list): List of GitLab project objects
        gl (gitlab.Gitlab): GitLab connection object
        
    Returns:
        tuple: (topic_counts, grouped_topics, projects_with_topics_count)
            - topic_counts: Counter object with counts for each topic
            - grouped_topics: Dictionary with counts for grouped topics
            - projects_with_topics_count: Number of projects with at least one topic
    """
    topic_counts = Counter()
    projects_with_topics = 0
    projects_topics = {}
    
    total_projects = len(projects)
    print(f"Analyzing topics for {total_projects} projects...")
    
    # Process projects in batches to avoid overwhelming the API
    batch_size = 100
    for i in range(0, total_projects, batch_size):
        batch = projects[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(total_projects + batch_size - 1)//batch_size}...")
        
        for idx, project in enumerate(batch):
            if idx % 10 == 0:
                print(f"  Processing project {i + idx + 1}/{total_projects}...")
            
            # Get topics for the project
            topics = get_project_topics(gl, project.id)
            
            # Store topics for this project
            projects_topics[project.id] = topics
            
            # Update counts
            if topics:
                projects_with_topics += 1
                topic_counts.update(topics)
            
        # Take a short break between batches
        if i + batch_size < total_projects:
            print("Taking a short break between batches...")
            time.sleep(2)
    
    # Group related topics (e.g., all dotnet topics)
    grouped_topics = defaultdict(int)
    for topic, count in topic_counts.items():
        # Extract the base topic (e.g., 'dotnet' from 'dotnet6')
        # This is a simple approach - you might need to customize this logic
        base_topic = ''.join([c for c in topic if not c.isdigit()])
        grouped_topics[base_topic] += count
    
    return topic_counts, dict(grouped_topics), projects_with_topics, projects_topics


def generate_topics_report(topic_counts, grouped_topics, projects_with_topics_count, total_projects, projects_topics, output_file=None):
    """
    Generate a report of topics analysis.
    
    Args:
        topic_counts (Counter): Counts for each topic
        grouped_topics (dict): Counts for grouped topics
        projects_with_topics_count (int): Number of projects with at least one topic
        total_projects (int): Total number of projects
        projects_topics (dict): Dictionary mapping project IDs to their topics
        output_file (str, optional): Path to save the CSV report
        
    Returns:
        pandas.DataFrame: DataFrame containing the topics report
    """
    # Create DataFrame for individual topics
    topics_df = pd.DataFrame({
        'topic': list(topic_counts.keys()),
        'project_count': list(topic_counts.values())
    })
    
    # Sort by project count in descending order
    topics_df = topics_df.sort_values('project_count', ascending=False).reset_index(drop=True)
    
    # Create DataFrame for grouped topics
    grouped_df = pd.DataFrame({
        'topic_group': list(grouped_topics.keys()),
        'total_projects': list(grouped_topics.values())
    })
    
    # Sort by total projects in descending order
    grouped_df = grouped_df.sort_values('total_projects', ascending=False).reset_index(drop=True)
    
    # Print summary
    print("\n=== Topics Analysis Summary ===")
    print(f"Total projects: {total_projects}")
    print(f"Projects with topics: {projects_with_topics_count} ({projects_with_topics_count/total_projects*100:.2f}%)")
    print(f"Unique topics: {len(topic_counts)}")
    print(f"Topic groups: {len(grouped_topics)}")
    
    print("\n=== Top 10 Topics ===")
    print(topics_df.head(10))
    
    print("\n=== Top 10 Topic Groups ===")
    print(grouped_df.head(10))
    
    # Save to CSV if output file is specified
    if output_file:
        # Save individual topics report
        topics_df.to_csv(f"{output_file}_individual.csv", index=False)
        print(f"Individual topics report saved to {output_file}_individual.csv")
        
        # Save grouped topics report
        grouped_df.to_csv(f"{output_file}_grouped.csv", index=False)
        print(f"Grouped topics report saved to {output_file}_grouped.csv")
        
        # Create a report of projects and their topics
        projects_topics_list = []
        for project_id, topics in projects_topics.items():
            if topics:  # Only include projects with topics
                projects_topics_list.append({
                    'project_id': project_id,
                    'topics': ', '.join(topics),
                    'topic_count': len(topics)
                })
        
        if projects_topics_list:
            projects_topics_df = pd.DataFrame(projects_topics_list)
            projects_topics_df = projects_topics_df.sort_values('topic_count', ascending=False).reset_index(drop=True)
            projects_topics_df.to_csv(f"{output_file}_projects.csv", index=False)
            print(f"Projects topics report saved to {output_file}_projects.csv")
    
    return topics_df, grouped_df


def main():
    parser = argparse.ArgumentParser(description='Generate a report of GitLab project topics')
    parser.add_argument('--url', help='GitLab URL (default: from environment variable GITLAB_URL)')
    parser.add_argument('--token', help='GitLab API token (default: from environment variable GITLAB_TOKEN)')
    parser.add_argument('--output', help='Output file prefix for CSV reports')
    parser.add_argument('--per-page', type=int, default=10, help='Number of items per page (default: 10)')
    
    args = parser.parse_args()
    
    # Get GitLab URL and token from arguments or environment variables
    gitlab_url = args.url or os.environ.get('GITLAB_URL')
    gitlab_token = args.token or os.environ.get('GITLAB_TOKEN')
    
    if not gitlab_url:
        print("Error: GitLab URL not provided. Use --url or set GITLAB_URL environment variable.")
        sys.exit(1)
    
    if not gitlab_token:
        print("Error: GitLab API token not provided. Use --token or set GITLAB_TOKEN environment variable.")
        sys.exit(1)
    
    # Connect to GitLab
    print(f"Connecting to GitLab instance at {gitlab_url}...")
    gl = connect_to_gitlab(gitlab_url, gitlab_token)
    
    # Get all projects with pagination
    print("Fetching all projects...")
    projects = get_all_projects_with_checkpoints(gl, per_page=args.per_page)
    
    # Analyze topics
    print("Analyzing project topics...")
    topic_counts, grouped_topics, projects_with_topics, projects_topics = analyze_topics(projects, gl)
    
    # Generate report
    output_file = args.output or 'gitlab_topics_report'
    generate_topics_report(
        topic_counts, 
        grouped_topics, 
        projects_with_topics, 
        len(projects),
        projects_topics,
        output_file
    )
    
    print("\nDone!")


if __name__ == "__main__":
    main()