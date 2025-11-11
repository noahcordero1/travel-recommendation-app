# ===================================
# DynamoDB Table - Destinations
# ===================================
resource "aws_dynamodb_table" "destinations" {
  name           = "${var.project_name}-destinations-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST" # Serverless pricing
  hash_key       = "city_id"

  attribute {
    name = "city_id"
    type = "S"
  }

  attribute {
    name = "country"
    type = "S"
  }

  global_secondary_index {
    name            = "CountryIndex"
    hash_key        = "country"
    projection_type = "ALL"
  }

  tags = {
    Name = "${var.project_name}-destinations"
  }
}

# ===================================
# DynamoDB Table - Airport Cache
# ===================================
resource "aws_dynamodb_table" "airport_cache" {
  name         = "${var.project_name}-airport-cache-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "location_key" # Format: "city|country"

  attribute {
    name = "location_key"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-airport-cache"
  }
}

# ===================================
# DynamoDB Table - Travel Index Results
# ===================================
resource "aws_dynamodb_table" "travel_index" {
  name         = "${var.project_name}-travel-index-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "timestamp"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-travel-index"
  }
}

# ===================================
# S3 Bucket - Data Storage
# ===================================
resource "aws_s3_bucket" "data_storage" {
  bucket = "${var.project_name}-data-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name = "${var.project_name}-data-storage"
  }
}

resource "aws_s3_bucket_versioning" "data_storage" {
  bucket = aws_s3_bucket.data_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_storage" {
  bucket = aws_s3_bucket.data_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Upload initial destinations data
resource "aws_s3_object" "destinations_data" {
  bucket       = aws_s3_bucket.data_storage.id
  key          = "static-data/destinations.json"
  source       = "${path.module}/data/destinations.json"
  etag         = filemd5("${path.module}/data/destinations.json")
  content_type = "application/json"
}

# ===================================
# Secrets Manager - API Keys
# ===================================
resource "aws_secretsmanager_secret" "api_keys" {
  name                    = "${var.project_name}-api-keys-${var.environment}"
  description             = "API keys for Travel Help services"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-api-keys"
  }
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  secret_id = aws_secretsmanager_secret.api_keys.id
  secret_string = jsonencode({
    openweather_api_key  = var.openweather_api_key
    huggingface_api_key  = var.huggingface_api_key
    amadeus_api_key      = var.amadeus_api_key
    amadeus_api_secret   = var.amadeus_api_secret
    openrouter_api_key   = var.openrouter_api_key
  })
}

# ===================================
# IAM Role - Lambda Execution
# ===================================
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-lambda-role"
  }
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution.name
}

# Custom policy for DynamoDB, S3, and Secrets Manager access
resource "aws_iam_role_policy" "lambda_permissions" {
  name = "${var.project_name}-lambda-permissions"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.destinations.arn,
          "${aws_dynamodb_table.destinations.arn}/index/*",
          aws_dynamodb_table.airport_cache.arn,
          aws_dynamodb_table.travel_index.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_storage.arn,
          "${aws_s3_bucket.data_storage.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.api_keys.arn
      }
    ]
  })
}

# ===================================
# Lambda Function - Weather Fetcher (Example)
# ===================================
resource "aws_lambda_function" "weather_fetcher" {
  filename         = "${path.module}/lambda_code/weather_fetcher.zip"
  function_name    = "${var.project_name}-weather-fetcher-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "index.handler"
  source_code_hash = fileexists("${path.module}/lambda_code/weather_fetcher.zip") ? filebase64sha256("${path.module}/lambda_code/weather_fetcher.zip") : null
  runtime         = "python3.11"
  timeout         = 30

  environment {
    variables = {
      DESTINATIONS_TABLE = aws_dynamodb_table.destinations.name
      SECRETS_ARN        = aws_secretsmanager_secret.api_keys.arn
      S3_BUCKET          = aws_s3_bucket.data_storage.id
    }
  }

  tags = {
    Name = "${var.project_name}-weather-fetcher"
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "weather_fetcher" {
  name              = "/aws/lambda/${aws_lambda_function.weather_fetcher.function_name}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-weather-fetcher-logs"
  }
}

# ===================================
# API Gateway - REST API
# ===================================
resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"
  description   = "Travel Help API Gateway"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 300
  }

  tags = {
    Name = "${var.project_name}-api"
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  tags = {
    Name = "${var.project_name}-api-stage"
  }
}

# Lambda integration with API Gateway
resource "aws_apigatewayv2_integration" "weather" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.weather_fetcher.invoke_arn
}

resource "aws_apigatewayv2_route" "weather" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /weather"
  target    = "integrations/${aws_apigatewayv2_integration.weather.id}"
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.weather_fetcher.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ===================================
# EventBridge Rule - Scheduled Weather Updates
# ===================================
resource "aws_cloudwatch_event_rule" "weather_schedule" {
  name                = "${var.project_name}-weather-schedule-${var.environment}"
  description         = "Trigger weather data update every 6 hours"
  schedule_expression = "rate(6 hours)"

  tags = {
    Name = "${var.project_name}-weather-schedule"
  }
}

resource "aws_cloudwatch_event_target" "weather_lambda" {
  rule      = aws_cloudwatch_event_rule.weather_schedule.name
  target_id = "WeatherFetcherLambda"
  arn       = aws_lambda_function.weather_fetcher.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.weather_fetcher.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weather_schedule.arn
}

# ===================================
# Lambda Function - Airport Resolver
# ===================================
resource "aws_lambda_function" "airport_resolver" {
  filename         = "${path.module}/lambda_code/airport_resolver.zip"
  function_name    = "${var.project_name}-airport-resolver-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "index.handler"
  source_code_hash = fileexists("${path.module}/lambda_code/airport_resolver.zip") ? filebase64sha256("${path.module}/lambda_code/airport_resolver.zip") : null
  runtime         = "python3.11"
  timeout         = 60  # Longer timeout for LLM API call

  environment {
    variables = {
      AIRPORT_CACHE_TABLE = aws_dynamodb_table.airport_cache.name
      SECRETS_ARN         = aws_secretsmanager_secret.api_keys.arn
    }
  }

  tags = {
    Name = "${var.project_name}-airport-resolver"
  }
}

# CloudWatch Log Group for Airport Resolver Lambda
resource "aws_cloudwatch_log_group" "airport_resolver" {
  name              = "/aws/lambda/${aws_lambda_function.airport_resolver.function_name}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-airport-resolver-logs"
  }
}

# API Gateway Integration for Airport Resolver
resource "aws_apigatewayv2_integration" "airport_resolver" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.airport_resolver.invoke_arn
}

resource "aws_apigatewayv2_route" "airport_resolver" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /resolve-airport"
  target    = "integrations/${aws_apigatewayv2_integration.airport_resolver.id}"
}

resource "aws_lambda_permission" "api_gateway_airport_resolver" {
  statement_id  = "AllowAPIGatewayInvokeAirportResolver"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.airport_resolver.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ===================================
# Lambda Function - Flight Pricer
# ===================================
resource "aws_lambda_function" "flight_pricer" {
  filename         = "${path.module}/lambda_code/flight_pricer.zip"
  function_name    = "${var.project_name}-flight-pricer-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "index.handler"
  source_code_hash = fileexists("${path.module}/lambda_code/flight_pricer.zip") ? filebase64sha256("${path.module}/lambda_code/flight_pricer.zip") : null
  runtime         = "python3.11"
  timeout         = 60  # Longer timeout for flight API calls

  environment {
    variables = {
      TRAVEL_INDEX_TABLE = aws_dynamodb_table.travel_index.name
      SECRETS_ARN        = aws_secretsmanager_secret.api_keys.arn
    }
  }

  tags = {
    Name = "${var.project_name}-flight-pricer"
  }
}

# CloudWatch Log Group for Flight Pricer Lambda
resource "aws_cloudwatch_log_group" "flight_pricer" {
  name              = "/aws/lambda/${aws_lambda_function.flight_pricer.function_name}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-flight-pricer-logs"
  }
}

# API Gateway Integration for Flight Pricer
resource "aws_apigatewayv2_integration" "flight_pricer" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.flight_pricer.invoke_arn
}

resource "aws_apigatewayv2_route" "flight_pricer" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /flight-prices"
  target    = "integrations/${aws_apigatewayv2_integration.flight_pricer.id}"
}

resource "aws_lambda_permission" "api_gateway_flight_pricer" {
  statement_id  = "AllowAPIGatewayInvokeFlightPricer"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.flight_pricer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ===================================
# Lambda Function - Index Calculator
# ===================================
resource "aws_lambda_function" "index_calculator" {
  filename         = "${path.module}/lambda_code/index_calculator.zip"
  function_name    = "${var.project_name}-index-calculator-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "index.handler"
  source_code_hash = fileexists("${path.module}/lambda_code/index_calculator.zip") ? filebase64sha256("${path.module}/lambda_code/index_calculator.zip") : null
  runtime         = "python3.11"
  timeout         = 120  # Longer timeout for calculating all destinations

  environment {
    variables = {
      DESTINATIONS_TABLE    = aws_dynamodb_table.destinations.name
      FLIGHT_PRICER_FUNCTION = aws_lambda_function.flight_pricer.function_name
    }
  }

  tags = {
    Name = "${var.project_name}-index-calculator"
  }
}

# CloudWatch Log Group for Index Calculator Lambda
resource "aws_cloudwatch_log_group" "index_calculator" {
  name              = "/aws/lambda/${aws_lambda_function.index_calculator.function_name}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-index-calculator-logs"
  }
}

# API Gateway Integration for Index Calculator
resource "aws_apigatewayv2_integration" "index_calculator" {
  api_id           = aws_apigatewayv2_api.main.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.index_calculator.invoke_arn
}

resource "aws_apigatewayv2_route" "index_calculator" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /travel-recommendations"
  target    = "integrations/${aws_apigatewayv2_integration.index_calculator.id}"
}

resource "aws_lambda_permission" "api_gateway_index_calculator" {
  statement_id  = "AllowAPIGatewayInvokeIndexCalculator"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.index_calculator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# IAM Policy for Index Calculator to invoke Flight Pricer
resource "aws_iam_role_policy" "lambda_invoke_permissions" {
  name = "${var.project_name}-lambda-invoke-permissions"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.flight_pricer.arn
        ]
      }
    ]
  })
}

# ===================================
# Data Sources
# ===================================
data "aws_caller_identity" "current" {}
