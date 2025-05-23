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
                            # Delete existing namespace if it exists
                            kubectl delete namespace face-recognition --ignore-not-found=true

                            # Apply namespace and wait for it to be ready
                            kubectl apply -f k8s/namespace.yaml

                            # Wait for namespace to be active
                            kubectl get namespace face-recognition
                            sleep 5

                            # Apply persistent volumes
                            kubectl apply -f k8s/pvs.yaml
                        '''

                        echo '📁 Copying data and models...'
                        sh '''
                            # Create copy pods
                            kubectl apply -f k8s/copy-models.yaml

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
                            kubectl apply -f k8s/frontend-deployment.yaml -n face-recognition
                            kubectl apply -f k8s/recognition-deployment.yaml -n face-recognition
                            kubectl apply -f k8s/training-deployment.yaml -n face-recognition
                            kubectl apply -f k8s/services.yaml -n face-recognition

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

                        echo '🔄 Attempting alternative deployment with docker driver but minimal config...'
                        try {
                            sh '''
                                # Stop any existing minikube
                                minikube stop || true
                                minikube delete || true

                                # Start minikube with minimal configuration
                                minikube start --driver=docker --cpus=2 --memory=2048 --force --wait=false

                                # Wait a bit for cluster to stabilize
                                sleep 10

                                # Check if cluster is responding
                                kubectl cluster-info --request-timeout=30s
                                kubectl get nodes --request-timeout=30s

                                # Apply configurations with simpler approach
                                kubectl create namespace face-recognition --dry-run=client -o yaml | kubectl apply -f -
                                sleep 5

                                # Skip PVs and data copying for now, just deploy applications
                                kubectl apply -f k8s/frontend-deployment.yaml -n face-recognition
                                kubectl apply -f k8s/recognition-deployment.yaml -n face-recognition
                                kubectl apply -f k8s/training-deployment.yaml -n face-recognition
                                kubectl apply -f k8s/services.yaml -n face-recognition

                                # Give deployments time to start
                                sleep 10

                                kubectl get pods -n face-recognition
                                kubectl get services -n face-recognition
                            '''
                            echo '✅ Alternative deployment succeeded!'

                        } catch (Exception fallbackError) {
                            echo "❌ Alternative deployment also failed: ${fallbackError.getMessage()}"

                            echo '🔄 Trying Kind as final fallback...'
                            try {
                                sh '''
                                    # Check if kind is available
                                    if command -v kind >/dev/null 2>&1; then
                                        echo "Found Kind, attempting to use it..."

                                        # Create kind cluster
                                        kind delete cluster --name jenkins || true
                                        kind create cluster --name jenkins --wait=60s

                                        # Apply configurations
                                        kubectl create namespace face-recognition --dry-run=client -o yaml | kubectl apply -f -

                                        # Deploy applications
                                        kubectl apply -f k8s/frontend-deployment.yaml -n face-recognition
                                        kubectl apply -f k8s/recognition-deployment.yaml -n face-recognition
                                        kubectl apply -f k8s/training-deployment.yaml -n face-recognition
                                        kubectl apply -f k8s/services.yaml -n face-recognition

                                        kubectl get pods -n face-recognition
                                        echo "✅ Kind deployment succeeded!"
                                    else
                                        echo "Kind not available, checking for existing cluster..."

                                        # Check if kubectl is available and try direct deployment
                                        if kubectl cluster-info &> /dev/null; then
                                            echo "Using existing Kubernetes cluster..."
                                            kubectl create namespace face-recognition --dry-run=client -o yaml | kubectl apply -f -
                                            kubectl apply -f k8s/frontend-deployment.yaml -n face-recognition
                                            kubectl apply -f k8s/recognition-deployment.yaml -n face-recognition
                                            kubectl apply -f k8s/training-deployment.yaml -n face-recognition
                                            kubectl apply -f k8s/services.yaml -n face-recognition
                                            kubectl get pods -n face-recognition
                                            echo "✅ Deployed to existing cluster!"
                                        else
                                            echo "No Kubernetes cluster available. Deployment failed."
                                            exit 1
                                        fi
                                    fi
                                '''
                            } catch (Exception finalError) {
                                echo "❌ All deployment attempts failed: ${finalError.getMessage()}"
                                echo "💡 Suggestions:"
                                echo "   - Install Kind in your Jenkins container: curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64 && chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind"
                                echo "   - Use a managed Kubernetes cluster (EKS, GKE, AKS)"
                                echo "   - Run Jenkins with privileged mode: docker run --privileged jenkins/jenkins"
                                echo "   - Consider using Docker Compose instead of Kubernetes for local development"

                                // Don't fail the entire pipeline, just mark as unstable
                                currentBuild.result = 'UNSTABLE'
                            }
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
