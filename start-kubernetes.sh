    minikube start --driver=docker --force

    kubectl apply -f k8s/namespace.yaml

    kubectl apply -f k8s/pvs.yaml

    kubectl apply -f k8s/copy-pod.yaml

    kubectl cp /home/aayushi/Desktop/spe_project/models/encodings.pkl face-recognition/copy-models:/app/models/encodings.pkl

    kubectl apply -f k8s/copy-data.yaml

    kubectl cp /home/aayushi/Desktop/spe_project/data/ face-recognition/copy-data:/app/

    kubectl cp /home/aayushi/Desktop/spe_project/data/ copy-data:/app/ -n face-recognition
    kubectl cp /home/aayushi/Desktop/spe_project/data/1 copy-data:/app/ -n face-recognition
    kubectl cp /home/aayushi/Desktop/spe_project/data/2 copy-data:/app/ -n face-recognition


    kubectl exec -n face-recognition -it copy-models -- ls -l /app/models

    kubectl exec -n face-recognition -it copy-data -- ls -l /app/data



    kubectl delete pod copy-models -n face-recognition


    kubectl delete pod copy-data -n face-recognition
    # Build images
    docker build -t upload_data:latest -f Dockerfile.upload_data .
    docker build -t recognition:latest -f Dockerfile.recognition .
    docker build -t frontend:latest -f Dockerfile.frontend .
    docker build -t training:latest -f Dockerfile.training .


    # Load images into minikube
    minikube image load recognition:latest

    minikube image load frontend:latest

    minikube image load training:latest

    minikube image load upload-data:latest


    # SSH into minikube
    minikube ssh

    # Create X11 socket directory
    sudo mkdir -p /tmp/.X11-unix
    sudo chmod 777 /tmp/.X11-unix

    # Exit minikube
    exit



    kubectl apply -f k8s/recognition-deployment.yaml

    eval $(minikube docker-env)  # So it builds inside Minikube's Docker daemon
    kubectl apply -f k8s/frontend-deployment.yaml
    kubectl apply -f k8s/upload-data.yaml
    kubectl apply -f k8s/training-deployment.yaml



    kubectl apply -f k8s/services.yaml
    # Check pods
    kubectl get pods -n face-recognition

    # Check services
    kubectl get services -n face-recognition

    # Get the frontend URL
    minikube service frontend-service -n face-recognition --url

    # Watch pod status
    kubectl get pods -n face-recognition -w

    # Check logs
    kubectl logs -n face-recognition -l app=recognition -f
    kubectl logs -n face-recognition -l app=frontend -f

    minikube service frontend-service -n face-recognition