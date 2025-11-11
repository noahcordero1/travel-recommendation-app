# AWS CLI Setup Guide

Complete guide to configure AWS CLI for your Travel Help project deployment.

## Step 1: Install AWS CLI

### macOS
```bash
brew install awscli
```

### Linux
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Windows
Download and run the installer from: https://aws.amazon.com/cli/

### Verify Installation
```bash
aws --version
# Expected output: aws-cli/2.x.x ...
```

## Step 2: Create AWS Account (if needed)

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow the registration process
4. **Important**: Enable MFA (Multi-Factor Authentication) for security

## Step 3: Create IAM User for Terraform

**Don't use your root account!** Create a dedicated IAM user:

### Via AWS Console:

1. Log in to AWS Console: https://console.aws.amazon.com/
2. Navigate to **IAM** service
3. Click **Users** → **Add users**
4. User name: `terraform-user`
5. Select: **Access key - Programmatic access**
6. Click **Next: Permissions**

### Attach Policies:

For development, attach these managed policies:
- `AmazonDynamoDBFullAccess`
- `AmazonS3FullAccess`
- `AWSLambda_FullAccess`
- `IAMFullAccess`
- `AmazonAPIGatewayAdministrator`
- `SecretsManagerReadWrite`
- `CloudWatchLogsFullAccess`
- `AmazonEventBridgeFullAccess`

**Or** create a custom policy with least privilege (see below).

### Save Your Credentials:

After creating the user, AWS will show:
- **Access Key ID**: AKIAIOSFODNN7EXAMPLE
- **Secret Access Key**: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

⚠️ **SAVE THESE NOW!** You can't view the secret again.

## Step 4: Configure AWS CLI

Run the configuration command:

```bash
aws configure
```

You'll be prompted for:

```
AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
Default region name [None]: eu-west-1
Default output format [None]: json
```

### Recommended Regions for Spain:

- `eu-west-1` (Ireland) - Most popular, lowest latency to Spain
- `eu-west-3` (Paris) - Closer geographically
- `eu-south-2` (Spain - Aragon) - Newest, limited services

**Recommendation**: Use `eu-west-1` for best service availability.

## Step 5: Verify Configuration

Test your AWS CLI connection:

```bash
# Check your identity
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/terraform-user"
# }

# List S3 buckets (should work even if empty)
aws s3 ls

# Check available regions
aws ec2 describe-regions --output table
```

## Step 6: Set Up AWS Credentials File

Your credentials are stored in `~/.aws/credentials`:

```bash
cat ~/.aws/credentials
```

Should show:
```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

Configuration file at `~/.aws/config`:
```bash
cat ~/.aws/config
```

Should show:
```ini
[default]
region = eu-west-1
output = json
```

## Step 7: (Optional) Configure Multiple Profiles

If you have multiple AWS accounts:

```bash
# Configure a new profile
aws configure --profile travel-help

# Use specific profile with Terraform
export AWS_PROFILE=travel-help

# Or in Terraform
AWS_PROFILE=travel-help terraform apply
```

## Security Best Practices

### 1. Enable MFA for IAM User

```bash
# List MFA devices
aws iam list-mfa-devices --user-name terraform-user
```

### 2. Rotate Access Keys Regularly

```bash
# Create new access key
aws iam create-access-key --user-name terraform-user

# Delete old access key (after updating config)
aws iam delete-access-key --user-name terraform-user --access-key-id OLD_KEY_ID
```

### 3. Never Commit Credentials

Add to `.gitignore`:
```
# AWS credentials
.aws/
terraform.tfvars
*.tfvars
!terraform.tfvars.example

# Terraform state (contains sensitive data)
*.tfstate
*.tfstate.*
.terraform/
```

### 4. Use AWS Secrets Manager

Store API keys in Secrets Manager (Terraform does this automatically):

```bash
# Retrieve secret
aws secretsmanager get-secret-value --secret-id travel-help-api-keys-dev
```

## Terraform-Specific AWS Setup

### Set AWS Region in Terraform

Option 1: Environment variable
```bash
export AWS_REGION=eu-west-1
export AWS_DEFAULT_REGION=eu-west-1
```

Option 2: In `terraform.tfvars`
```hcl
aws_region = "eu-west-1"
```

Option 3: Via command line
```bash
terraform apply -var="aws_region=eu-west-1"
```

## Troubleshooting

### "Unable to locate credentials"

```bash
# Check if credentials exist
cat ~/.aws/credentials

# Reconfigure if needed
aws configure
```

### "Access Denied" Errors

Your IAM user needs more permissions. Add policies in IAM console.

### "Region not specified"

```bash
# Set default region
aws configure set region eu-west-1
```

### Check Current Configuration

```bash
# View all settings
aws configure list

# View specific profile
aws configure list --profile travel-help
```

## Cost Management Setup

### 1. Set Up Billing Alerts

```bash
# Enable billing alerts (one-time)
aws ce put-cost-anomaly-monitor \
  --monitor-name "travel-help-costs" \
  --monitor-type CUSTOM
```

### 2. Create Budget

Via AWS Console:
1. Go to **AWS Billing** → **Budgets**
2. Create budget: Monthly cost budget
3. Set amount: $50 (or your limit)
4. Add email alerts at 80% and 100%

## Quick Reference

```bash
# View current identity
aws sts get-caller-identity

# List available regions
aws ec2 describe-regions --query 'Regions[].RegionName' --output table

# Check permissions (example)
aws iam get-user

# List Lambda functions
aws lambda list-functions

# List DynamoDB tables
aws dynamodb list-tables

# List S3 buckets
aws s3 ls

# View CloudWatch logs
aws logs describe-log-groups
```

## Ready to Deploy!

Once AWS CLI is configured, return to the main deployment:

```bash
cd /Users/noahcordero/Desktop/CloudProject
terraform init
terraform apply
```

See **QUICKSTART.md** for deployment steps.

## Additional Resources

- AWS CLI Documentation: https://docs.aws.amazon.com/cli/
- IAM Best Practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- AWS Free Tier: https://aws.amazon.com/free/
- Terraform AWS Provider: https://registry.terraform.io/providers/hashicorp/aws/latest/docs

## Support

If you encounter issues:
1. Verify credentials: `aws sts get-caller-identity`
2. Check region: `aws configure get region`
3. Test permissions: `aws s3 ls`
4. Review IAM policies in AWS Console
