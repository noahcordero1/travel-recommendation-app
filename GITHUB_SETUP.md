# GitHub Actions Deployment Setup

This guide will help you set up automatic deployment to AWS when you push to the `main` branch.

## Prerequisites

You need your AWS credentials (these will be stored as GitHub Secrets):
- **Access Key ID**: Your AWS access key
- **Secret Access Key**: Your AWS secret key
- **Region**: `eu-west-1`

## Step 1: Push Code to GitHub

First, initialize your git repository and push to GitHub:

```bash
cd /Users/noahcordero/Desktop/CloudProject

# Initialize git if not already done
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit - Travel recommendation app with AWS Lambda and S3 frontend"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/travel-recommendation-app.git

# Push to main branch
git push -u origin main
```

## Step 2: Add AWS Credentials as GitHub Secrets

1. Go to your GitHub repository: `https://github.com/YOUR_USERNAME/travel-recommendation-app`

2. Click on **Settings** (top menu)

3. In the left sidebar, click **Secrets and variables** → **Actions**

4. Click **New repository secret**

5. Add the first secret:
   - **Name**: `AWS_ACCESS_KEY_ID`
   - **Value**: Your AWS Access Key ID
   - Click **Add secret**

6. Add the second secret:
   - Click **New repository secret** again
   - **Name**: `AWS_SECRET_ACCESS_KEY`
   - **Value**: Your AWS Secret Access Key
   - Click **Add secret**

## Step 3: Verify Workflow is Set Up

The GitHub Actions workflow is already configured in `.github/workflows/deploy.yml`

It will automatically:
- Trigger on every push to the `main` branch
- Package all Lambda functions
- Deploy Lambda functions to AWS
- Upload frontend to S3 bucket

## Step 4: Test the Deployment

1. Make any small change to your code (e.g., add a comment)
2. Commit and push:
   ```bash
   git add .
   git commit -m "Test deployment"
   git push
   ```

3. Go to your GitHub repository and click **Actions** tab

4. You should see a workflow running

5. Once complete, verify:
   - Lambda functions are updated
   - Frontend is deployed: http://travel-help-frontend-515214870577.s3-website-eu-west-1.amazonaws.com/

## What Gets Deployed

### Lambda Functions Updated:
- `travel-help-weather-fetcher-dev`
- `travel-help-airport-resolver-dev`
- `travel-help-flight-pricer-dev`
- `travel-help-index-calculator-dev`

### Frontend Deployed to:
- S3 Bucket: `travel-help-frontend-515214870577`
- URL: http://travel-help-frontend-515214870577.s3-website-eu-west-1.amazonaws.com/

## Troubleshooting

### Deployment Fails with "Access Denied"

Make sure:
1. GitHub Secrets are set correctly (check spelling)
2. AWS credentials have the necessary permissions:
   - `lambda:UpdateFunctionCode`
   - `s3:PutObject`
   - `s3:ListBucket`

### Lambda Update Fails

Check that Lambda function names match:
- In AWS: Go to Lambda console and verify function names
- In workflow file: Check `.github/workflows/deploy.yml` function names

### Frontend Not Updating

1. Check S3 bucket permissions allow public read access
2. Try hard refresh in browser (Ctrl+Shift+R or Cmd+Shift+R)
3. Check if CloudFront is being used (adds caching)

## Security Notes

- Never commit AWS credentials to git (they're in GitHub Secrets only)
- The `.gitignore` file prevents sensitive files from being committed
- Rotate AWS credentials periodically for security

## Manual Deployment (Alternative)

If you need to deploy manually without GitHub Actions:

```bash
# Package Lambda functions
./package_lambda.sh

# Deploy Lambda functions
aws lambda update-function-code --function-name travel-help-airport-resolver-dev --zip-file fileb://lambda_code/airport_resolver.zip
aws lambda update-function-code --function-name travel-help-flight-pricer-dev --zip-file fileb://lambda_code/flight_pricer.zip
aws lambda update-function-code --function-name travel-help-index-calculator-dev --zip-file fileb://lambda_code/index_calculator.zip
aws lambda update-function-code --function-name travel-help-weather-fetcher-dev --zip-file fileb://lambda_code/weather_fetcher.zip

# Deploy frontend
aws s3 cp frontend/index.html s3://travel-help-frontend-515214870577/ --cache-control "no-cache"
```
