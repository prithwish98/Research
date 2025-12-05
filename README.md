# DDL Formatter

This repository contains a Python application to format SQL DDL files. It provides a GUI, a command-line interface, and automation for CI/CD pipelines.

## Features

- Standardizes `CREATE TABLE/VIEW` to `CREATE OR REPLACE TABLE/VIEW`.
- Prefixes table/view names with a Jinja variable `{{edw_db_name}}`.
- Moves trailing commas to the start of the next line.
- Moves the opening parenthesis of a `CREATE TABLE` statement to a new line.
- Converts all SQL keywords to uppercase.

---

## Azure DevOps Pull Request Integration

You can integrate the DDL formatter directly into your Azure DevOps pull request workflow to automatically format `.sql` files. The pipeline will run on any PR that modifies `.sql` files, format them if they contain the word "DDL", and push the changes back to the source branch.

### Step 1: Create the Pipeline YAML File

Create a file named `azure-pipelines.yml` in the root of your repository with the following content. This file defines the automation steps.

```yaml
# azure-pipelines.yml
# This pipeline automatically formats SQL DDL files in a pull request.

pr:
  branches:
    include:
      - main # Or your default branch, e.g., 'master'
  paths:
    include:
      - '**.sql'

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.11'
  displayName: 'Use Python 3.11'

- script: |
    echo "Searching for DDL files to format..."
    # Find all .sql files, check if they contain 'DDL', and format them if they do.
    find . -type f -name "*.sql" | while read -r file; do
      if grep -iq 'DDL' "$file"; then
        echo "Formatting '$file'..."
        python ddl_formatter_combined_4.py --mode file --input "$file" --output "$file"
      fi
    done
  displayName: 'Run DDL Formatter on changed files'

- script: |
    # Configure Git user for the commit
    git config --global user.name "Azure DevOps Build"
    git config --global user.email "$(Build.RequestedForEmail)"

    # Check if the formatter made any changes
    if [[ -n $(git status -s) ]]; then
      echo "Found formatted files. Committing and pushing changes..."
      git add .
      git commit -m "Automated DDL Formatting [skip ci]"
      # Push the changes back to the pull request's source branch
      git push
    else
      echo "No formatting changes were needed."
    fi
  displayName: 'Commit and Push Formatted Files'
  env:
    # The System.AccessToken is used to authenticate the git push.
    # Permissions must be granted to the Build Service for this to work.
    GIT_AUTHORIZATION: "Bearer $(System.AccessToken)"
```

### Step 2: Create the Pipeline in Azure DevOps

1.  Go to your Azure DevOps project and navigate to **Pipelines**.
2.  Click **"New pipeline"** or **"Create Pipeline"**.
3.  Select **"Azure Repos Git"** as the location of your code.
4.  Select your repository.
5.  Choose **"Existing Azure Pipelines YAML file"**.
6.  Select `/azure-pipelines.yml` from the file path dropdown.
7.  Click **"Continue"** and then **"Save"**. You don't need to run it yet.

### Step 3: Grant Permissions to the Build Service

For the pipeline to push changes back to a pull request, the build service identity needs "Contribute" permissions.

1.  Navigate to **Project Settings** > **Repositories**.
2.  Select your repository.
3.  Go to the **Security** tab.
4.  In the user search box, find your project's build service identity. It will be named `[Your Project Name] Build Service ([Your Organization Name])`.
5.  Set the **Contribute** permission to **Allow**.

### Step 4: Set Up a Branch Policy

To make this pipeline run automatically on pull requests, you need to set it up as a build validation policy.

1.  Navigate to **Repos** > **Branches**.
2.  Find your main branch (e.g., `main`), click the three dots, and select **Branch policies**.
3.  Under **Build Validation**, click **"+"** to add a new policy.
4.  Select the pipeline you just created from the **Build pipeline** dropdown.
5.  Set the **Policy requirement** to **Required**.
6.  Click **Save**.

With this setup, any new pull request targeting your main branch with `.sql` file changes will automatically trigger the formatter.