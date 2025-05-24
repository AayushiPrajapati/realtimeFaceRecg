# helm install elasticsearch elastic/elasticsearch -f elasticsearch-values.yaml


# helm install kibana elastic/kibana


# helm install logstash elastic/logstash


# helm install filebeat elastic/filebeat


# kubectl port-forward service/kibana-kibana 5601:5601




create namespace monitoring 

# kubectl apply -f elasticsearch-values.yaml -n monitoring
kubectl apply -f elasticsearch.yaml -n monitoring
kubectl apply -f kibana.yaml -n monitoring
# kubectl apply -f logstash-deployment.yaml -n monitoring 


kubectl apply -f filebeat.yaml -n monitoring
kubectl apply -f filebeat-demonset.yaml -n monitoring
kubectl get pods -n monitoring -l app=filebeat
kubectl logs -n monitoring <filebeat-pod-name>
kubectl port-forward svc/elasticsearch-clusterip 9201:9200 -n monitoring
curl http://localhost:9201/_cat/indices?v


kubectl port-forward svc/kibana 5601:5601 -n monitoring
