#!/bin/bash

NAMESPACE="face-recognition"
APP_LABEL="recognition"
LOCAL_FILE="$HOME/Desktop/spe_project/models/encodings.pkl"
TEMP_FILE="/tmp/encodings.pkl"

# Copy file into minikube VM
echo "[INFO] Copying encodings.pkl into Minikube VM..."
minikube ssh "rm -f $TEMP_FILE"
minikube cp "$LOCAL_FILE" "$TEMP_FILE"

# Get pod and container name
POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app="$APP_LABEL" -o jsonpath="{.items[0].metadata.name}")
CONTAINER_NAME=$(kubectl get pod "$POD_NAME" -n "$NAMESPACE" -o jsonpath="{.spec.containers[0].name}")

echo "[INFO] Inside Minikube: copying to pod $POD_NAME container $CONTAINER_NAME..."
minikube ssh "kubectl cp $TEMP_FILE $NAMESPACE/$POD_NAME:/app/models/encodings.pkl -c $CONTAINER_NAME"

# Clean up
minikube ssh "rm -f $TEMP_FILE"

# Restart pod
kubectl delete pod -n "$NAMESPACE" "$POD_NAME"

echo "[INFO] Done. File should now be inside the container."
    