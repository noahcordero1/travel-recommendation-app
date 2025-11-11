# Quick Start Guide - Travel Help

Get your Travel Help infrastructure deployed in 5 minutes!

## Prerequisites Checklist

- [ ] AWS account with credentials configured (`aws configure`)
- [ ] Terraform installed (`terraform --version`)
- [ ] Python 3.11+ installed (`python3 --version`)

## Deployment in 3 Steps

### Step 1: Initialize Terraform

```bash
cd /Users/noahcordero/Desktop/CloudProject
terraform init
```

### Step 2: Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted. Deployment takes ~2-3 minutes.

### Step 3: Add Your API Keys

```bash
# Get your API Gateway URL
terraform output api_gateway_url

# Update API keys in Secrets Manager
aws secretsmanager update-secret \
  --secret-id $(terraform output -raw secrets_manager_arn) \
  --secret-string '{
    "openweather_api_key": "YOUR_KEY_HERE",
    "huggingface_api_key": "YOUR_KEY_HERE",
    "flight_api_key": "YOUR_KEY_HERE"
  }'
```

## Test Your Deployment

```bash
# Test the weather endpoint
curl "$(terraform output -raw api_gateway_url)/weather"
```

## What Was Deployed?

- **3 DynamoDB Tables**: destinations, airport-cache, travel-index
- **1 S3 Bucket**: Static data storage with 10 pre-loaded cities
- **1 Lambda Function**: Weather fetcher (auto-runs every 6 hours)
- **1 API Gateway**: RESTful API endpoint
- **1 Secrets Manager**: Secure API key storage

## Getting API Keys

### OpenWeatherMap (Free)
1. Sign up: https://openweathermap.org/api
2. Get free API key (60 calls/min)

### Hugging Face (Free)
1. Sign up: https://huggingface.co/
2. Settings → Access Tokens → Create token

### Flight API (Amadeus Recommended)
1. Sign up: https://developers.amadeus.com/
2. Free tier: 2000 calls/month

## View Your Resources

```bash
# All outputs
terraform output

# Specific resources
terraform output destinations_table_name
terraform output s3_bucket_name
```

## Next Steps

1. ✅ Test weather API endpoint
2. ✅ Verify data in DynamoDB
3. ✅ Check CloudWatch logs
4. 🔨 Add more Lambda functions (airport resolver, flight fetcher, etc.)
5. 🔨 Implement frontend with Mapbox
6. 🔨 Add Cognito authentication

## Destroy Everything

```bash
terraform destroy
```

Type `yes` to remove all resources.

## Need Help?

- See **README.md** for detailed documentation
- Check Lambda logs: `aws logs tail /aws/lambda/travel-help-weather-fetcher-dev --follow`
- Validate config: `terraform validate`

---

**Estimated Cost**: $2-10/month for development usage
