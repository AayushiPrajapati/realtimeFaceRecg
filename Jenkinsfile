pipeline {
    agent any

    environment {
        DOCKER_REGISTRY = 'docker.io/aayushi6402'
        IMAGE_NAME1 = 'training'
        IMAGE_NAME2 = 'frontend'
        IMAGE_NAME3 = 'recognition'
        IMAGE_TAG = 'latest'
        KUBECONFIG = "${env.HOME}/.kube/config"
    }

    stages {
        stage('Ensure Minikube is Running') {
            steps {
                echo '🔍 Checking Kubernetes status...'
                sh '''
                    if ! kubectl cluster-info > /dev/null 2>&1; then
                        echo "⚠️ Minikube not running. Starting it now..."
                        minikube start --driver=docker --cpus=4 --memory=4096 --force
                    else
                        echo "✅ Minikube already running."
                        kubectl cluster-info
                    fi
                '''
            }
        }

        stage('Checkout Code') {
            steps {
                git url: 'https://github.com/AayushiPrajapati/realtimeFaceRecg.git', branch: 'main'
            }
        }

        stage('Docker Login') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                        sh 'echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin'
                    }
                }
            }
        }

        stage('Prepare Data') {
            steps {
                sh '''
                    mkdir -p ./data ./models
                    cp -r /var/jenkins_data/data/* ./data/
                    cp /var/jenkins_data/models/encodings.pkl ./models/
                '''
            }
        }

        stage('Build & Push Docker Images') {
            steps {
                sh """
                    docker build -t $DOCKER_REGISTRY/$IMAGE_NAME1:$IMAGE_TAG -f Dockerfile.training .
                    docker build -t $DOCKER_REGISTRY/$IMAGE_NAME2:$IMAGE_TAG -f Dockerfile.frontend .
                    docker build -t $DOCKER_REGISTRY/$IMAGE_NAME3:$IMAGE_TAG -f Dockerfile.recognition .

                    docker push $DOCKER_REGISTRY/$IMAGE_NAME1:$IMAGE_TAG
                    docker push $DOCKER_REGISTRY/$IMAGE_NAME2:$IMAGE_TAG
                    docker push $DOCKER_REGISTRY/$IMAGE_NAME3:$IMAGE_TAG
                """
            }
        }

        stage('K8s Namespace & Volumes') {
            steps {
                sh '''
                    kubectl delete namespace face-recognition --ignore-not-found=true
                    kubectl apply -f k8s/namespace.yaml
                    sleep 3
                    kubectl apply -f k8s/pvs.yaml
                '''
            }
        }

        stage('Copy Data & Models to Pod') {
            steps {
                sh '''
                    kubectl apply -f k8s/copy-models.yaml
                    kubectl wait --for=condition=Ready pod/copy-models -n face-recognition --timeout=60s
                    kubectl cp ./models/encodings.pkl face-recognition/copy-models:/app/models/encodings.pkl || echo "Warning: models copy failed"

                    kubectl apply -f k8s/copy-data.yaml
                    kubectl wait --for=condition=Ready pod/copy-data -n face-recognition --timeout=60s
                    kubectl cp ./data/ face-recognition/copy-data:/app/ || echo "Warning: data copy failed"
                '''
            }
        }

        stage('Deploy Application Pods') {
            steps {
                sh '''
                    kubectl apply -f k8s/frontend-deployment.yaml -n face-recognition
                    kubectl apply -f k8s/recognition-deployment.yaml -n face-recognition
                    kubectl apply -f k8s/training-deployment.yaml -n face-recognition
                    kubectl apply -f k8s/services.yaml -n face-recognition
                '''
            }
        }

        stage('Wait for App Pods to Be Running') {
            steps {
                sh '''
                    for i in {1..30}; do
                        echo "⏳ Waiting for face-recognition pods..."
                        PENDING=$(kubectl get pods -n face-recognition | grep -v NAME | grep -v Running | wc -l)
                        if [ "$PENDING" -eq 0 ]; then
                            echo "✅ All pods are Running"
                            break
                        fi
                        sleep 10
                    done
                    kubectl get pods -n face-recognition
                '''
            }
        }

        stage('Expose Frontend') {
            steps {
                sh '''
                    nohup minikube tunnel > /dev/null 2>&1 &
                    sleep 5
                    NODE_PORT=$(kubectl get service frontend -n face-recognition -o=jsonpath="{.spec.ports[0].nodePort}")
                    NODE_IP=$(minikube ip)
                    echo "✅ App is available at: http://$NODE_IP:$NODE_PORT"
                '''
            }
        }
    }

    post {
        success {
            echo '✅ Project deployed successfully.'
        }
        failure {
            echo '❌ Project deployment failed.'
        }
    }
}
