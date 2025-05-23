kubectl create namespace monitoring

kubectl apply -f k8s/prometheus-rbac.yaml -n monitoring
kubectl apply -f k8s/prometheus-config.yaml -n monitoring
kubectl apply -f k8s/prometheus-deployment.yaml -n monitoring

kubectl get pods -n monitoring
kubectl get svc -n monitoring
kubectl apply -f k8s/grafana-deployment.yaml -n monitoring
kubectl get pods -n monitoring
kubectl get svc -n monitoring
minikube ip
http://192.168.49.2:32000





http://prometheus.monitoring.svc.cluster.local:9090



kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3001:80
kubectl port-forward svc/prometheus -n monitoring 9090:9090


kubectl rollout restart deployment/frontend -n face-recognition
