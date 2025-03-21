# Ask Aithena Agent Deployment Instructions

This document provides instructions for deploying the Ask Aithena Agent in a local Kubernetes environment.

## Prerequisites

- Docker installed and running
- Kubernetes cluster running locally (Minikube, Kind, or Docker Desktop Kubernetes)
- kubectl configured to use your local cluster
- Git repository cloned locally

## Build and Deploy Steps

### 1. Build the Docker Image

First, build the Docker image locally:

```bash
# Navigate to the agent directory
cd agents/ask-aithena-agent

# Build the Docker image
docker build -t ask-aithena-agent:latest .
```

### 2. Load the Image into Kubernetes

Depending on your local Kubernetes setup, use one of the following methods:

#### For Minikube
```bash
# Configure Docker to use Minikube's Docker daemon
eval $(minikube docker-env)

# Rebuild the image (now using Minikube's Docker daemon)
docker build -t ask-aithena-agent:latest .
```

#### For Kind
```bash
# Load the image into Kind
kind load docker-image ask-aithena-agent:latest
```

#### For Docker Desktop Kubernetes
No additional steps needed - the local image will be available automatically.

### 3. Configure the Deployment

Before applying the deployment, make sure to:

1. Update the prompts directory path in `ask-aithena-agent-depl.yaml`:
```yaml
volumes:
  - name: prompts-volume
    hostPath:
      path: /your/actual/path/to/prompts  # Update this path
      type: Directory
```

2. Verify the environment variables in `ask-aithena-agent-depl.yaml`:
   - LITELLM_URL should point to your LiteLLM service
   - LITELLM_API_KEY should be set correctly
   - Other environment variables should match your setup

### 4. Apply the Deployment

```bash
# Apply the deployment
kubectl apply -f kubernetes/ask-aithena-agent-depl.yaml

# Apply the service
kubectl apply -f kubernetes/ask-aithena-agent-service.yaml

# Check the deployment status
kubectl get deployments
kubectl get pods
```

### 5. Verify the Deployment

```bash
# Check if the pod is running
kubectl get pods -l app=ask-aithena-agent

# Check the logs
kubectl logs -l app=ask-aithena-agent

# Port-forward to test locally (if needed)
kubectl port-forward service/ask-aithena-agent-service 8000:8000
```

## Troubleshooting

### Common Issues

1. **ImagePullBackOff Error**
   - This is expected with `imagePullPolicy: Never`
   - Verify that you built the image locally
   - Check if you loaded the image correctly for your Kubernetes setup

2. **Pod Crash Loop**
   - Check the logs: `kubectl logs -l app=ask-aithena-agent`
   - Verify environment variables are set correctly
   - Ensure the prompts directory is mounted correctly

3. **Service Not Accessible**
   - Verify the service is running: `kubectl get svc`
   - Check if pods are running and ready
   - Try port-forwarding to test connectivity

### Useful Commands

```bash
# Get detailed pod information
kubectl describe pod -l app=ask-aithena-agent

# Get deployment status
kubectl get deployment ask-aithena-agent -o yaml

# Restart the deployment
kubectl rollout restart deployment ask-aithena-agent

# Delete and recreate everything
kubectl delete -f kubernetes/ask-aithena-agent-depl.yaml
kubectl delete -f kubernetes/ask-aithena-agent-service.yaml
kubectl apply -f kubernetes/ask-aithena-agent-depl.yaml
kubectl apply -f kubernetes/ask-aithena-agent-service.yaml
```

## Development Workflow

When making changes to the agent:

1. Make your code changes
2. Rebuild the Docker image:
   ```bash
   docker build -t ask-aithena-agent:latest .
   ```
3. Load the new image into your Kubernetes cluster (see step 2 above)
4. Restart the deployment:
   ```bash
   kubectl rollout restart deployment ask-aithena-agent
   ```

## Environment Variables Reference

Here are the key environment variables used in the deployment:

```yaml
# Service Information
LOGFIRE_SERVICE_NAME: "ask-aithena-agent"
LOGFIRE_SERVICE_VERSION: "1.0.0"

# LiteLLM Configuration
LITELLM_URL: "http://litellm-service:4000/v1"
LITELLM_API_KEY: "your-api-key"

# Model Configuration
CHAT_MODEL: "llama3.1:8b"
SEMANTICS_MODEL: "llama3.2"
SEMANTICS_TEMPERATURE: "0.2"
RERANK_MODEL: "azure-gpt-4o"
RERANK_TEMPERATURE: "0.3"

# Embedding Configuration
EMBED_MODEL: "nomic"
EMBEDDING_TABLE: "openalex.nomic_embed_text_768"
SIMILARITY_N: "10"

# Other Configuration
PROMPTS_DIR: "/opt/executables/prompts"
AITHENA_LOG_LEVEL: "DEBUG"
USE_RABBITMQ: "true"
``` 