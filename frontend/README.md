# Travel Help Frontend

Simple, clean frontend for the Travel Help platform.

## Live Website

**URL**: http://travel-help-frontend-515214870577.s3-website-eu-west-1.amazonaws.com

## Features

- **Real-time data** from your AWS Lambda backend
- **Responsive design** - works on desktop, tablet, and mobile
- **Clean UI** with gradient background and card layout
- **Quality of Life metrics** for each destination
- **Weather data display** (when API keys are configured)
- **Zero dependencies** - pure HTML, CSS, and JavaScript

## What It Shows

### For Each Destination:
- City name and country
- IATA airport code
- Current weather (temperature, description, humidity, wind)
- Quality of Life metrics:
  - Beer prices
  - Michelin restaurants
  - Food quality score
  - Walkability score
  - Public transport score
  - Safety score

## How It Works

1. Frontend calls your API Gateway endpoint: `GET /weather`
2. Lambda function fetches weather data from OpenWeatherMap API
3. Results are displayed in a beautiful card grid
4. Auto-loads on page load

## Current Status

✅ **Working**:
- Infrastructure connection
- 10 destination cities loaded
- Quality of Life metrics displayed
- Responsive design

⏳ **Waiting for API keys**:
- Live weather data (shows placeholder until API keys added)

## Updating the Frontend

To update the website:

```bash
cd /Users/noahcordero/Desktop/CloudProject/frontend

# Edit index.html
nano index.html

# Upload to S3
aws s3 cp index.html s3://travel-help-frontend-515214870577/index.html --content-type "text/html"
```

## Future Enhancements

When you're ready to expand:

1. **Add user input** - Allow users to enter their home city
2. **Airport resolver** - Integrate Hugging Face API for nearest airport
3. **Flight prices** - Show flight costs from user's location
4. **Travel Index** - Calculate and display weighted scores
5. **Sorting/Filtering** - Let users customize rankings
6. **Map view** - Add Mapbox GL for visual destination display
7. **User accounts** - Integrate Cognito authentication
8. **Favorites** - Save preferred destinations

## Tech Stack

- **HTML5** - Structure
- **CSS3** - Styling with flexbox and grid
- **Vanilla JavaScript** - No frameworks, no build process
- **Fetch API** - AJAX calls to backend
- **AWS S3** - Static website hosting

## Notes

- Single HTML file - easy to maintain
- No build process required
- Fast loading (< 20KB)
- Works in all modern browsers
- Mobile-friendly responsive design

## Testing Locally

To test locally before uploading:

```bash
# Simple Python server
cd /Users/noahcordero/Desktop/CloudProject/frontend
python3 -m http.server 8000

# Open browser to http://localhost:8000
```

## Cost

**S3 Static Website Hosting**:
- First 1GB free tier
- ~$0.50/month for typical usage
- No Lambda or compute costs for frontend
