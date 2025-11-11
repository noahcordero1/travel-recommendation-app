variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-west-1" # Ireland - close to Spain
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "travel-help"
}

# API Keys - will be stored in Secrets Manager
variable "openweather_api_key" {
  description = "OpenWeatherMap API key"
  type        = string
  default     = "placeholder-will-update-later"
  sensitive   = true
}

variable "huggingface_api_key" {
  description = "Hugging Face API key"
  type        = string
  default     = "placeholder-will-update-later"
  sensitive   = true
}

variable "amadeus_api_key" {
  description = "Amadeus API key"
  type        = string
  default     = "placeholder-will-update-later"
  sensitive   = true
}

variable "amadeus_api_secret" {
  description = "Amadeus API secret"
  type        = string
  default     = "placeholder-will-update-later"
  sensitive   = true
}

variable "openrouter_api_key" {
  description = "OpenRouter API key for LLM airport resolution"
  type        = string
  default     = "placeholder-will-update-later"
  sensitive   = true
}
