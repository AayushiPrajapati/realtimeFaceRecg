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
        stage('Checkout') {
            steps {
                echo '📥 Cloning repository...'
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
                echo '📂 Copying required data and models...'
                sh '''
                    mkdir -p ./data ./models
                    cp -r /var/jenkins_data/data/1 ./data/
                    cp -r /var/jenkins_data/data/2 ./data/
                    cp /var/jenkins_data/models/encodings.pkl ./models/
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                echo '🐳 Building Docker images...'
                sh """
                    docker build -t $DOCKER_REGISTRY/$IMAGE_NAME1:$IMAGE_TAG -f Dockerfile.training .
                    docker build -t $DOCKER_REGISTRY/$IMAGE_NAME2:$IMAGE_TAG -f Dockerfile.frontend .
                    docker build -t $DOCKER_REGISTRY/$IMAGE_NAME3:$IMAGE_TAG -f Dockerfile.recognition .
                """
            }
        }

        stage('Push Docker Images') {
            steps {
                echo '📦 Pushing Docker images to Docker Hub...'
                sh """
                    docker push $DOCKER_REGISTRY/$IMAGE_NAME1:$IMAGE_TAG
                    docker push $DOCKER_REGISTRY/$IMAGE_NAME2:$IMAGE_TAG
                    docker push $DOCKER_REGISTRY/$IMAGE_NAME3:$IMAGE_TAG
                """
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo '🚀 Deploying to Kubernetes...'
                script {
                    try {
                        sh '''
                            minikube stop || true
                            minikube delete || true

                            minikube start --driver=docker --cpus=4 --memory=4096 --force

                            kubectl cluster-info
                            kubectl get nodes

                            kubectl apply -f k8s/namespace.yaml
                            kubectl apply -f k8s/pvs.yaml

                            kubectl apply -f k8s/copy-pod.yaml
                            kubectl wait --for=condition=Ready pod/copy-models -n face-recognition --timeout=60s
                            kubectl cp ./models/encodings.pkl face-recognition/copy-models:/app/models/encodings.pkl

                            kubectl apply -f k8s/copy-data.yaml
                            kubectl wait --for=condition=Ready pod/copy-data -n face-recognition --timeout=60s
                            kubectl cp ./data/ face-recognition/copy-data:/app/

                            kubectl exec -n face-recognition copy-models -- ls -l /app/models || true
                            kubectl exec -n face-recognition copy-data -- ls -l /app/data || true

                            kubectl delete pod copy-models -n face-recognition --ignore-not-found=true
                            kubectl delete pod copy-data -n face-recognition --ignore-not-found=true

                            eval $(minikube docker-env) || true
                            
                            kubectl apply -f k8s/frontend-deployment.yaml
                            kubectl apply -f k8s/recognition-deployment.yaml
                            kubectl apply -f k8s/training-deployment.yaml
                            kubectl apply -f k8s/services.yaml

                            kubectl wait --for=condition=Available deployment/frontend -n face-recognition --timeout=300s || echo "Frontend deployment timeout"
                            kubectl wait --for=condition=Available deployment/recognition -n face-recognition --timeout=300s || echo "Recognition deployment timeout"
                            kubectl wait --for=condition=Available deployment/training -n face-recognition --timeout=300s || echo "Training deployment timeout"

                            kubectl get pods -n face-recognition
                            kubectl get services -n face-recognition
                            minikube service frontend-service -n face-recognition --url || echo "Service URL not available"

                            echo "=== Frontend Logs ==="
                            kubectl logs -n face-recognition -l app=frontend --tail=20 || true

                            echo "=== Recognition Logs ==="
                            kubectl logs -n face-recognition -l app=recognition --tail=20 || true

                            echo "=== Training Logs ==="
                            kubectl logs -n face-recognition -l app=training --tail=20 || true
                        '''
                    } catch (Exception e) {
                        echo "❌ Primary deployment failed: ${e.getMessage()}"
                        echo '🔄 Trying fallback...'

                        try {
                            sh '''
                                minikube stop || true
                                minikube delete || true

                                minikube start --driver=none --memory=2048 --cpus=2 --force

                                kubectl cluster-info
                                kubectl get nodes

                                kubectl apply -f k8s/namespace.yaml
                                kubectl apply -f k8s/pvs.yaml
                                kubectl apply -f k8s/frontend-deployment.yaml
                                kubectl apply -f k8s/recognition-deployment.yaml
                                kubectl apply -f k8s/training-deployment.yaml
                                kubectl apply -f k8s/services.yaml
                                kubectl get pods -n face-recognition
                            '''
                        } catch (Exception fallbackError) {
                            echo "❌ Alternative deployment also failed: ${fallbackError.getMessage()}"
                            echo "💡 Suggestions:"
                            echo "   - Check Kubernetes configuration"
                            echo "   - Consider using a hosted Kubernetes cluster for production"
                            currentBuild.result = 'FAILURE'
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            echo '🧹 Cleaning up...'
        }
        success {
            echo '✅ Build and deployment succeeded!'
        }
        failure {
            echo '❌ Build or deployment failed.'
        }
    }
}
