#!/bin/bash

# Script to package Lambda functions for deployment

echo "Packaging Lambda functions..."

# Create a temporary directory for packaging
TEMP_DIR="lambda_temp"

# Package weather_fetcher Lambda
echo "Packaging weather_fetcher..."
mkdir -p "$TEMP_DIR"
cd lambda_code

# Install dependencies to temp directory
pip install -r requirements.txt -t "../$TEMP_DIR" --quiet

# Copy Lambda function code
cp weather_fetcher.py "../$TEMP_DIR/index.py"

# Create zip file
cd "../$TEMP_DIR"
zip -r ../lambda_code/weather_fetcher.zip . > /dev/null

# Clean up
cd ..
rm -rf "$TEMP_DIR"

# Package airport_resolver Lambda
echo "Packaging airport_resolver..."
mkdir -p "$TEMP_DIR"
cd lambda_code

# Install dependencies to temp directory (reuse same requirements.txt)
pip install -r requirements.txt -t "../$TEMP_DIR" --quiet

# Copy Lambda function code
cp airport_resolver.py "../$TEMP_DIR/index.py"

# Copy airports data file (required by airport_resolver)
cp airports_data.json "../$TEMP_DIR/airports_data.json"

# Create zip file
cd "../$TEMP_DIR"
zip -r ../lambda_code/airport_resolver.zip . > /dev/null

# Clean up
cd ..
rm -rf "$TEMP_DIR"

# Package flight_pricer Lambda
echo "Packaging flight_pricer..."
mkdir -p "$TEMP_DIR"
cd lambda_code

# Install dependencies to temp directory (reuse same requirements.txt)
pip install -r requirements.txt -t "../$TEMP_DIR" --quiet

# Copy Lambda function code
cp flight_pricer.py "../$TEMP_DIR/index.py"

# Create zip file
cd "../$TEMP_DIR"
zip -r ../lambda_code/flight_pricer.zip . > /dev/null

# Clean up
cd ..
rm -rf "$TEMP_DIR"

# Package index_calculator Lambda
echo "Packaging index_calculator..."
mkdir -p "$TEMP_DIR"
cd lambda_code

# Install dependencies to temp directory (reuse same requirements.txt)
pip install -r requirements.txt -t "../$TEMP_DIR" --quiet

# Copy Lambda function code
cp index_calculator.py "../$TEMP_DIR/index.py"

# Create zip file
cd "../$TEMP_DIR"
zip -r ../lambda_code/index_calculator.zip . > /dev/null

# Clean up
cd ..
rm -rf "$TEMP_DIR"

echo "Lambda packaging complete!"
echo "Created: lambda_code/weather_fetcher.zip"
echo "Created: lambda_code/airport_resolver.zip"
echo "Created: lambda_code/flight_pricer.zip"
echo "Created: lambda_code/index_calculator.zip"
