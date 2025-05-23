minikube start --driver=docker --force
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/pvs.yaml
kubectl apply -f k8s/copy-pod.yaml
kubectl cp /home/aayushi/Desktop/spe_project/models/encodings.pkl face-recognition/copy-models:/app/models/encodings.pkl

kubectl apply -f k8s/copy-data.yaml
kubectl cp /home/aayushi/Desktop/spe_project/data/ face-recognition/copy-data:/app/


kubectl exec -n face-recognition -it copy-models -- ls -l /app/models
kubectl exec -n face-recognition -it copy-data -- ls -l /app/data

kubectl delete pod copy-models -n face-recognition
kubectl delete pod copy-data -n face-recognition

eval $(minikube docker-env) 
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/recognition-deployment.yaml
# kubectl apply -f k8s/upload-data.yaml
kubectl apply -f k8s/training-deployment.yaml

kubectl apply -f k8s/services.yaml


kubectl get pods -n face-recognition
kubectl get services -n face-recognition

# Get frontend URL
minikube service frontend-service -n face-recognition --url

# Watch logs
kubectl logs -n face-recognition -l app=recognition -f
kubectl logs -n face-recognition -l app=frontend -f
kubectl logs -n face-recognition -l app=training -f  