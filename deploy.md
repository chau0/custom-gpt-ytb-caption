# Deploying YouTube Caption API to Google Cloud Run

This guide provides step-by-step instructions for deploying the FastAPI-based YouTube Caption API to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account**: Active Google Cloud account with billing enabled
2. **Google Cloud CLI**: Install the [gcloud CLI](https://cloud.google.com/sdk/docs/install)
3. **Docker**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
4. **Python 3.11+**: For local testing (optional)

## Setup Google Cloud Project

### 1. Create and Configure Project

```bash
# Create new project (replace PROJECT_ID with your preferred ID)
export PROJECT_ID="youtube-caption-api"
gcloud projects create $PROJECT_ID

# Set the project as default
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Set Environment Variables

```bash
export REGION="us-central1"  # Choose your preferred region
export SERVICE_NAME="youtube-caption-api"
export IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
```

## Local Testing (Optional)

### 1. Set up Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Locally

```bash
# Start the FastAPI server
python main.py

# Or use uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Test the API

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test caption endpoint
curl -X POST http://localhost:8000/func_ytb_caption \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "chunk_size": 1000,
    "max_chunks": 2
  }'
```

## Docker Build and Test

### 1. Build Docker Image Locally

```bash
# Build the image
docker build -t $SERVICE_NAME .

# Run container locally
docker run -p 8000:8000 -e PORT=8000 $SERVICE_NAME

# Test in another terminal
curl http://localhost:8000/health
```

## Deploy to Cloud Run

### 1. Build and Push to Container Registry

```bash
# Build and push using Cloud Build
gcloud builds submit --tag $IMAGE_NAME

# Alternative: Build locally and push
docker build -t $IMAGE_NAME .
docker push $IMAGE_NAME
```

### 2. Deploy to Cloud Run

```bash
# Deploy the service
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 100 \
  --set-env-vars "CHUNK_SIZE=5000,MAX_CHUNKS=5"
```

### 3. Get Service URL

```bash
# Get the service URL
gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)'
```

## Environment Variables Configuration

Set environment variables for your deployment:

```bash
# Basic configuration
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --set-env-vars "CHUNK_SIZE=5000,MAX_CHUNKS=5"

# If using proxy (optional)
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --set-env-vars "USE_PROXY=1,WEBSHARE_PROXY_USERNAME=your_username,WEBSHARE_PROXY_PASSWORD=your_password"
```

## Testing the Deployed Service

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health

# Test caption endpoint
curl -X POST $SERVICE_URL/func_ytb_caption \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "chunk_size": 1000,
    "max_chunks": 2
  }'
```

## Custom Domain Setup (Optional)

### 1. Map Custom Domain

```bash
# Map domain to service
gcloud run domain-mappings create \
  --service $SERVICE_NAME \
  --domain your-domain.com \
  --region $REGION
```

### 2. Update DNS Records

Follow the instructions provided by the domain mapping command to update your DNS records.

## Monitoring and Logging

### 1. View Logs

```bash
# View recent logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" \
  --limit 50 \
  --format "table(timestamp,textPayload)"

# Stream logs in real-time
gcloud logs tail "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME"
```

### 2. Set up Monitoring

```bash
# Enable Cloud Monitoring API
gcloud services enable monitoring.googleapis.com

# Create uptime check (replace URL with your service URL)
gcloud alpha monitoring uptime create \
  --display-name="YouTube Caption API Health Check" \
  --http-check-path="/health" \
  --hostname="your-service-url"
```

## Scaling Configuration

### 1. Update Service Configuration

```bash
# Update scaling and resource limits
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --memory 1Gi \
  --cpu 2 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 100 \
  --timeout 300
```

## CI/CD with Cloud Build (Optional)

### 1. Create cloudbuild.yaml

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/youtube-caption-api:$COMMIT_SHA', '.']
  
  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/youtube-caption-api:$COMMIT_SHA']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: 'gcloud'
    args: [
      'run', 'deploy', 'youtube-caption-api',
      '--image', 'gcr.io/$PROJECT_ID/youtube-caption-api:$COMMIT_SHA',
      '--region', 'us-central1',
      '--platform', 'managed',
      '--allow-unauthenticated'
    ]

images:
  - 'gcr.io/$PROJECT_ID/youtube-caption-api:$COMMIT_SHA'
```

### 2. Set up Build Trigger

```bash
# Connect to GitHub repository (interactive)
gcloud builds triggers create github \
  --repo-name=your-repo-name \
  --repo-owner=your-github-username \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

## Troubleshooting

### Common Issues

1. **503 Service Unavailable**: Check container logs for startup errors
2. **Timeout Errors**: Increase timeout or optimize YouTube API calls
3. **Memory Issues**: Increase memory allocation or optimize chunking
4. **Cold Start Latency**: Consider min-instances > 0 for production

### Debug Commands

```bash
# Check service status
gcloud run services describe $SERVICE_NAME --region $REGION

# View revision details
gcloud run revisions list --service $SERVICE_NAME --region $REGION

# Check build history
gcloud builds list --limit 10
```

## Cost Optimization

1. **Set appropriate memory/CPU**: Start with 512Mi/1 CPU
2. **Use min-instances sparingly**: Only for production with consistent traffic
3. **Optimize container size**: Use multi-stage builds if needed
4. **Monitor usage**: Set up billing alerts

## Security Best Practices

1. **Use IAM roles**: Don't use `--allow-unauthenticated` for sensitive APIs
2. **Secrets management**: Use Google Secret Manager for sensitive data
3. **VPC connectivity**: Use VPC connector for private resources
4. **Regular updates**: Keep dependencies updated

## API Documentation

Once deployed, your API documentation will be available at:
- Interactive docs: `https://your-service-url/docs`
- OpenAPI schema: `https://your-service-url/openapi.json`