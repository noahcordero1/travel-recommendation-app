output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "destinations_table_name" {
  description = "DynamoDB Destinations table name"
  value       = aws_dynamodb_table.destinations.name
}

output "airport_cache_table_name" {
  description = "DynamoDB Airport Cache table name"
  value       = aws_dynamodb_table.airport_cache.name
}

output "travel_index_table_name" {
  description = "DynamoDB Travel Index table name"
  value       = aws_dynamodb_table.travel_index.name
}

output "s3_bucket_name" {
  description = "S3 bucket for data storage"
  value       = aws_s3_bucket.data_storage.id
}

output "secrets_manager_arn" {
  description = "Secrets Manager ARN for API keys"
  value       = aws_secretsmanager_secret.api_keys.arn
}

output "lambda_execution_role_arn" {
  description = "IAM role ARN for Lambda execution"
  value       = aws_iam_role.lambda_execution.arn
}

output "weather_fetcher_function_name" {
  description = "Weather fetcher Lambda function name"
  value       = aws_lambda_function.weather_fetcher.function_name
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "airport_resolver_function_name" {
  description = "Airport resolver Lambda function name"
  value       = aws_lambda_function.airport_resolver.function_name
}

output "flight_pricer_function_name" {
  description = "Flight pricer Lambda function name"
  value       = aws_lambda_function.flight_pricer.function_name
}

output "index_calculator_function_name" {
  description = "Index calculator Lambda function name"
  value       = aws_lambda_function.index_calculator.function_name
}
