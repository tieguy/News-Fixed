# SonarQube GitHub Actions Setup

This repository uses GitHub Actions to automatically scan code with SonarQube Cloud on every push.

## Setup Instructions

### 1. Add SONAR_TOKEN to GitHub Secrets

1. Go to your GitHub repository: https://github.com/tieguy/News-Fixed
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `SONAR_TOKEN`
5. Value: `5190520b4222619ccdb36fca233c84e098e733c1` (your SonarQube token)
6. Click **Add secret**

### 2. Verify Workflow

After adding the secret and pushing this commit, the workflow will:
- Run automatically on every push to `main`
- Run on pull requests
- Send results to SonarQube Cloud

### 3. View Results

- **SonarQube Cloud**: https://sonarcloud.io/project/overview?id=tieguy_News-Fixed
- **GitHub Actions**: https://github.com/tieguy/News-Fixed/actions

## Manual Trigger

You can also manually trigger a scan from the GitHub Actions tab:
1. Go to **Actions** → **SonarQube Analysis**
2. Click **Run workflow**
