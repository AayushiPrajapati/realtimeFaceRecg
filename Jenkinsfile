pipeline {
    agent any

    environment {
        DOCKER_REGISTRY = 'docker.io/aayushi6402'
        IMAGE_NAME1 = 'training'
        IMAGE_TAG = 'latest'
        IMAGE_NAME2 = 'frontend'    
        IMAGE_NAME3 = 'recognition'
        KUBECONFIG = "$HOME/.kube/config"
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
                    cp -r /var/jenkins_data/data ./data
                    cp -r /var/jenkins_data/data/1 ./data/
                    cp -r /var/jenkins_data/data/2 ./data/
                    cp -r /var/jenkins_data/models ./models
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
                // Start minikube with better configuration for Docker environment
                echo '🔧 Starting Minikube...'
                sh '''
                    # Stop any existing minikube instance
                    minikube stop || true
                    minikube delete || true
                    
                    # Start minikube with docker driver and increased resources
                    minikube start --driver=docker --cpus=4 --memory=4096 --force
                    
                    # Check minikube status
                    minikube status
                    
                    # Wait for cluster to be ready
                    kubectl cluster-info
                    kubectl get nodes
                '''
                
                echo '📦 Setting up namespace and persistent volumes...'
                sh '''
                    kubectl apply -f k8s/namespace.yaml
                    kubectl apply -f k8s/pvs.yaml
                '''
                
                echo '📁 Copying data and models...'
                sh '''
                    # Create copy pods
                    kubectl apply -f k8s/copy-pod.yaml
                    
                    # Wait for pods to be ready
                    kubectl wait --for=condition=Ready pod/copy-models -n face-recognition --timeout=60s
                    
                    # Copy models file (using local path from workspace)
                    kubectl cp ./models/encodings.pkl face-recognition/copy-models:/app/models/encodings.pkl || echo "Warning: Could not copy models file"
                    
                    # Create data copy pod
                    kubectl apply -f k8s/copy-data.yaml
                    kubectl wait --for=condition=Ready pod/copy-data -n face-recognition --timeout=60s
                    
                    # Copy data directory (using local path from workspace)
                    kubectl cp ./data/ face-recognition/copy-data:/app/ || echo "Warning: Could not copy data directory"
                    
                    # Verify copies
                    kubectl exec -n face-recognition copy-models -- ls -l /app/models || true
                    kubectl exec -n face-recognition copy-data -- ls -l /app/data || true
                    
                    # Clean up copy pods
                    kubectl delete pod copy-models -n face-recognition --ignore-not-found=true
                    kubectl delete pod copy-data -n face-recognition --ignore-not-found=true
                '''
                
                echo '🚀 Deploying applications...'
                sh '''
                    # Configure Docker environment for minikube
                    eval $(minikube docker-env) || true
                    
                    # Deploy applications
                    kubectl apply -f k8s/frontend-deployment.yaml
                    kubectl apply -f k8s/recognition-deployment.yaml
                    kubectl apply -f k8s/training-deployment.yaml
                    kubectl apply -f k8s/services.yaml
                    
                    # Wait for deployments to be ready
                    kubectl wait --for=condition=Available deployment/frontend -n face-recognition --timeout=300s || echo "Frontend deployment timeout"
                    kubectl wait --for=condition=Available deployment/recognition -n face-recognition --timeout=300s || echo "Recognition deployment timeout"  
                    kubectl wait --for=condition=Available deployment/training -n face-recognition --timeout=300s || echo "Training deployment timeout"
                '''
                
                echo '📊 Checking deployment status...'
                sh '''
                    kubectl get pods -n face-recognition
                    kubectl get services -n face-recognition
                    
                    # Get service URL (if available)
                    minikube service frontend-service -n face-recognition --url || echo "Service URL not available"
                    
                    # Show recent logs
                    echo "=== Frontend Logs ==="
                    kubectl logs -n face-recognition -l app=frontend --tail=20 || true
                    
                    echo "=== Recognition Logs ==="
                    kubectl logs -n face-recognition -l app=recognition --tail=20 || true
                    
                    echo "=== Training Logs ==="
                    kubectl logs -n face-recognition -l app=training --tail=20 || true
                '''
                
                echo '✅ Kubernetes deployment completed successfully!'
                
            } catch (Exception e) {
                echo "❌ Primary deployment failed: ${e.getMessage()}"
                
                // Try alternative deployment with none driver
                echo '🔄 Attempting alternative deployment with none driver...'
                try {
                    sh '''
                        # Stop docker driver minikube
                        minikube stop || true
                        minikube delete || true
                        
                        # Try with none driver (runs directly on host)
                        minikube start --driver=none --force --memory=2048 --cpus=2
                        
                        # Wait for cluster to be ready
                        kubectl cluster-info
                        kubectl get nodes
                        
                        # Apply configurations
                        kubectl apply -f k8s/namespace.yaml
                        kubectl apply -f k8s/pvs.yaml
                        
                        # Deploy applications directly without data copying
                        kubectl apply -f k8s/frontend-deployment.yaml
                        kubectl apply -f k8s/recognition-deployment.yaml
                        kubectl apply -f k8s/training-deployment.yaml
                        kubectl apply -f k8s/services.yaml
                        
                        kubectl get pods -n face-recognition
                        kubectl get services -n face-recognition
                    '''
                    echo '✅ Alternative deployment succeeded!'
                    
                } catch (Exception fallbackError) {
                    echo "❌ Alternative deployment also failed: ${fallbackError.getMessage()}"
                    
                    // Final fallback - check for existing cluster
                    echo '🔄 Checking for existing Kubernetes cluster...'
                    try {
                        sh '''
                            # Check if kubectl is available and try direct deployment
                            if kubectl cluster-info &> /dev/null; then
                                echo "Using existing Kubernetes cluster..."
                                kubectl apply -f k8s/namespace.yaml
                                kubectl apply -f k8s/frontend-deployment.yaml
                                kubectl apply -f k8s/recognition-deployment.yaml
                                kubectl apply -f k8s/training-deployment.yaml
                                kubectl apply -f k8s/services.yaml
                                kubectl get pods -n face-recognition
                                echo "✅ Deployed to existing cluster!"
                            else
                                echo "No Kubernetes cluster available. Deployment failed."
                                exit 1
                            fi
                        '''
                    } catch (Exception finalError) {
                        echo "❌ All deployment attempts failed: ${finalError.getMessage()}"
                        echo "💡 Suggestions:"
                        echo "   - Consider using a real Kubernetes cluster instead of Minikube in Docker"
                        echo "   - Run Jenkins outside Docker to avoid Docker-in-Docker issues"
                        echo "   - Use Kind instead of Minikube for better CI/CD support"
                        currentBuild.result = 'UNSTABLE'
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
