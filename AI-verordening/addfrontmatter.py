import os
import re

def has_front_matter(content):
    """Check if the content already has Jekyll front matter."""
    return content.startswith('---')

def add_front_matter_to_md_files(directory, layout="page"):
    # Walk through the directory and its subdirectories
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".md"):
                file_path = os.path.join(root, filename)
                
                # Read the original content of the Markdown file
                with open(file_path, 'r', encoding='utf-8') as file:
                    original_content = file.read()
                
                # Skip files that already have front matter
                if has_front_matter(original_content):
                    print(f"Skipping {file_path} (front matter already present)")
                    continue
                
                # Extract the first header (assumed to be the title)
                match = re.search(r'^# (.+)', original_content, re.MULTILINE)
                if match:
                    title = match.group(1).strip()
                else:
                    title = filename.replace('.md', '')  # Fallback to filename if no header found
                
                # Define the front matter
                front_matter = f"---\nlayout: {layout}\ntitle: \"{title}\"\n---\n\n"
                
                # Write the front matter followed by the original content
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(front_matter + original_content)
                
                print(f"Added front matter to {file_path}")

# Specify the directory containing your Markdown files
directory_path = "/Users/werkjoas/Documents/GitHub/aicompdocs/AI-verordening"

# Call the function to add front matter
add_front_matter_to_md_files(directory_path)