# Travel Help - Cloud Infrastructure (Terraform)

A lightweight, serverless AWS infrastructure for the Travel Help intelligent travel recommendation platform.

## Overview

This Terraform configuration deploys the foundational AWS infrastructure for Travel Help:
- **DynamoDB** tables for destinations, airport cache, and travel index data
- **S3** bucket for static data storage
- **Lambda** functions for serverless compute
- **API Gateway** for RESTful endpoints
- **Secrets Manager** for secure API key storage
- **EventBridge** for scheduled weather updates
- **IAM** roles and policies for secure access

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
   ```bash
   aws configure
   ```
3. **Terraform** installed (v1.0+)
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```
4. **Python 3.11+** (for Lambda functions)
5. **API Keys** (to be added after deployment):
   - OpenWeatherMap API key
   - Hugging Face API key
   - Flight API key (Amadeus/Skyscanner)

## Project Structure

```
CloudProject/
├── main.tf                    # Main infrastructure resources
├── providers.tf               # AWS provider configuration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars           # Variable values (create this)
├── data/
│   └── destinations.json      # 10 hardcoded destination cities
├── lambda_code/
│   ├── weather_fetcher.py     # Weather fetching Lambda
│   ├── requirements.txt       # Python dependencies
│   └── weather_fetcher.zip    # Packaged Lambda (generated)
└── package_lambda.sh          # Lambda packaging script
```

## Deployment Steps

### 1. Initialize Terraform

```bash
cd /Users/noahcordero/Desktop/CloudProject
terraform init
```

This downloads required providers and initializes the backend.

### 2. Package Lambda Functions

```bash
./package_lambda.sh
```

This creates the Lambda deployment package with all dependencies.

### 3. Review and Deploy

```bash
# Preview changes
terraform plan

# Deploy infrastructure
terraform apply
```

Type `yes` when prompted to confirm deployment.

### 4. Configure API Keys

After deployment, update the API keys in AWS Secrets Manager:

```bash
# Get the secret ARN from Terraform outputs
terraform output secrets_manager_arn

# Update the secret with your actual API keys
aws secretsmanager update-secret \
  --secret-id $(terraform output -raw secrets_manager_arn) \
  --secret-string '{
    "openweather_api_key": "YOUR_OPENWEATHER_KEY",
    "huggingface_api_key": "YOUR_HUGGINGFACE_KEY",
    "flight_api_key": "YOUR_FLIGHT_API_KEY"
  }'
```

Or update via AWS Console:
1. Go to AWS Secrets Manager
2. Find the secret named `travel-help-api-keys-dev`
3. Click "Retrieve secret value" → "Edit"
4. Update the JSON with your actual API keys

### 5. Test the Weather Endpoint

```bash
# Get the API Gateway URL
API_URL=$(terraform output -raw api_gateway_url)

# Test the weather endpoint
curl "${API_URL}/weather"
```

## Important Resources Created

Run `terraform output` to see all created resources:

| Resource | Description |
|----------|-------------|
| **API Gateway URL** | Base URL for API endpoints |
| **DynamoDB Tables** | destinations, airport-cache, travel-index |
| **S3 Bucket** | Static data and archives |
| **Lambda Function** | weather-fetcher (runs every 6 hours) |
| **Secrets Manager** | API keys storage |

## Configuration

### Change AWS Region

Edit `variables.tf` or create `terraform.tfvars`:

```hcl
aws_region = "eu-west-3"  # Paris
```

### Change Environment

```hcl
environment = "prod"
```

### Update Scheduled Weather Fetch Frequency

In `main.tf`, find `aws_cloudwatch_event_rule.weather_schedule` and modify:

```hcl
schedule_expression = "rate(3 hours)"  # Default is 6 hours
```

## API Keys Setup

### OpenWeatherMap
1. Sign up at https://openweathermap.org/api
2. Get a free API key (60 calls/minute)

### Hugging Face
1. Sign up at https://huggingface.co/
2. Go to Settings → Access Tokens
3. Create a new token with read permissions

### Flight API Options

**Option 1: Amadeus (Recommended)**
- Sign up at https://developers.amadeus.com/
- Free tier: 2000 calls/month
- Good for testing

**Option 2: Skyscanner**
- Requires RapidAPI subscription
- https://rapidapi.com/skyscanner/api/skyscanner-flight-search

## Testing the Infrastructure

### 1. Verify DynamoDB Tables

```bash
# List all tables
aws dynamodb list-tables

# Scan destinations table
aws dynamodb scan \
  --table-name $(terraform output -raw destinations_table_name) \
  --max-items 5
```

### 2. Check S3 Bucket

```bash
# List bucket contents
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/

# View destinations file
aws s3 cp s3://$(terraform output -raw s3_bucket_name)/static-data/destinations.json -
```

### 3. Invoke Lambda Manually

```bash
aws lambda invoke \
  --function-name $(terraform output -raw weather_fetcher_function_name) \
  --payload '{}' \
  response.json

cat response.json
```

### 4. Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/$(terraform output -raw weather_fetcher_function_name) --follow
```

## Next Steps

After the basic infrastructure is deployed, you can extend it with:

1. **Additional Lambda Functions**:
   - Airport resolver (Hugging Face integration)
   - Flight price fetcher
   - Index calculator
   - Data enrichment processor

2. **Authentication**:
   - Add Cognito user pool
   - Implement API Gateway authorizers

3. **Frontend**:
   - Deploy React/Vue app to S3 + CloudFront
   - Configure Mapbox GL for visualization

4. **Monitoring**:
   - CloudWatch dashboards
   - SNS alerts for errors
   - Cost monitoring

5. **Step Functions**:
   - Orchestrate the full data pipeline
   - Handle complex workflows

## Cost Estimation

With the current lightweight setup:

- **DynamoDB**: Pay-per-request (~$1-5/month for light usage)
- **Lambda**: First 1M requests free, then $0.20 per 1M requests
- **S3**: $0.023 per GB/month (~$0.10/month)
- **API Gateway**: First 1M calls free, then $1 per million
- **Secrets Manager**: $0.40/month per secret

**Estimated monthly cost for development: $2-10**

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

Type `yes` when prompted. This will delete all AWS resources created by Terraform.

## Troubleshooting

### Lambda Package Error

If you see "Error creating Lambda function", ensure the zip file exists:

```bash
./package_lambda.sh
ls -lh lambda_code/weather_fetcher.zip
```

### Permission Errors

Ensure your AWS credentials have sufficient permissions:
- Lambda: Full access
- DynamoDB: Full access
- S3: Full access
- IAM: Create roles and policies
- API Gateway: Full access

### API Keys Not Working

Verify the secret format:

```bash
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw secrets_manager_arn) \
  --query SecretString \
  --output text | jq
```

## Documentation Links

- **OpenWeatherMap API**: https://openweathermap.org/api/one-call-api
- **Hugging Face Inference API**: https://huggingface.co/docs/api-inference/
- **Amadeus Flight API**: https://developers.amadeus.com/self-service/category/flights
- **AWS Lambda Python**: https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs

## Support

For issues or questions:
1. Check CloudWatch Logs for Lambda errors
2. Review Terraform state: `terraform show`
3. Validate configuration: `terraform validate`

## License

MIT License - Feel free to modify and extend!

