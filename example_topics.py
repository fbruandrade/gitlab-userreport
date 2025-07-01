#!/usr/bin/env python3
"""
Example script demonstrating how to use the GitLab Topics Report Generator
programmatically.
"""

import os
from topics_report import connect_to_gitlab, get_all_projects_with_checkpoints, analyze_topics, generate_topics_report

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

    # Get all projects with pagination (using a smaller page size for stability)
    print("Fetching all projects...")
    projects = get_all_projects_with_checkpoints(gl, per_page=10)
    print(f"Found {len(projects)} total projects")

    # Analyze topics
    print("Analyzing project topics...")
    topic_counts, grouped_topics, projects_with_topics, projects_topics = analyze_topics(projects, gl)
    
    # Print some basic statistics
    print(f"\nProjects with topics: {projects_with_topics} out of {len(projects)} ({projects_with_topics/len(projects)*100:.2f}%)")
    print(f"Unique topics found: {len(topic_counts)}")
    
    # Generate reports
    output_file = 'example_topics_report'
    topics_df, grouped_df = generate_topics_report(
        topic_counts,
        grouped_topics,
        projects_with_topics,
        len(projects),
        projects_topics,
        output_file
    )
    
    # Additional analysis examples
    
    # Example 1: Find projects with a specific topic
    print("\n=== Example Analysis ===")
    specific_topic = 'python'  # Replace with a topic you're interested in
    if specific_topic in topic_counts:
        print(f"Projects with '{specific_topic}' topic: {topic_counts[specific_topic]}")
        
        # Find projects that have this topic
        projects_with_specific_topic = [
            project_id for project_id, topics in projects_topics.items() 
            if specific_topic in topics
        ]
        print(f"First 5 project IDs with '{specific_topic}' topic: {projects_with_specific_topic[:5]}")
    else:
        print(f"No projects found with '{specific_topic}' topic")
    
    # Example 2: Find the most common topic combinations
    print("\n=== Common Topic Combinations ===")
    topic_combinations = Counter()
    for project_id, topics in projects_topics.items():
        if len(topics) > 1:  # Only consider projects with multiple topics
            # Create a frozenset of topics to use as a dictionary key
            topic_set = frozenset(topics)
            topic_combinations[topic_set] += 1
    
    # Print the top 5 most common topic combinations
    print("Top 5 most common topic combinations:")
    for i, (topic_set, count) in enumerate(topic_combinations.most_common(5)):
        if i < 5:  # Limit to top 5
            print(f"  - {', '.join(topic_set)}: {count} projects")
    
    # Example 3: Find projects with the most topics
    print("\n=== Projects with Most Topics ===")
    projects_by_topic_count = sorted(
        [(project_id, len(topics)) for project_id, topics in projects_topics.items() if topics],
        key=lambda x: x[1],
        reverse=True
    )
    
    print("Top 5 projects with most topics:")
    for i, (project_id, topic_count) in enumerate(projects_by_topic_count[:5]):
        print(f"  - Project ID {project_id}: {topic_count} topics - {', '.join(projects_topics[project_id])}")
    
    print("\nDone!")

if __name__ == "__main__":
    from collections import Counter
    main()