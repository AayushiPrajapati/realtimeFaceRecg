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
                            minikube stop || true
                            minikube delete || true
                            minikube start --driver=docker --cpus=4 --memory=4096 --force
                            minikube status
                            kubectl cluster-info
                        '''

                        echo '📦 Setting up namespace and persistent volumes...'
                        sh '''
                            kubectl delete namespace face-recognition --ignore-not-found=true
                            kubectl apply -f k8s/namespace.yaml
                            sleep 5
                            kubectl apply -f k8s/pvs.yaml
                        '''

                        echo '📁 Copying data and models...'
                        sh '''
                            kubectl apply -f k8s/copy-models.yaml
                            kubectl wait --for=condition=Ready pod/copy-models -n face-recognition --timeout=60s
                            kubectl cp ./models/encodings.pkl face-recognition/copy-models:/app/models/encodings.pkl || echo "Warning: Could not copy models file"

                            kubectl apply -f k8s/copy-data.yaml
                            kubectl wait --for=condition=Ready pod/copy-data -n face-recognition --timeout=60s
                            kubectl cp ./data/ face-recognition/copy-data:/app/ || echo "Warning: Could not copy data directory"
                        '''

                        echo '🚀 Deploying apps...'
                        sh '''
                            kubectl apply -f k8s/frontend-deployment.yaml -n face-recognition
                            kubectl apply -f k8s/recognition-deployment.yaml -n face-recognition
                            kubectl apply -f k8s/training-deployment.yaml -n face-recognition
                            kubectl apply -f k8s/services.yaml -n face-recognition
                        '''

                        echo '⏳ Waiting for pods to be Running...'
                        sh '''
                            for i in {1..30}; do
                                echo "Check $i: Waiting for all pods to be Running..."
                                PENDING=$(kubectl get pods -n face-recognition | grep -v NAME | grep -v Running | wc -l)
                                if [ "$PENDING" -eq 0 ]; then
                                    echo "✅ All pods are Running"
                                    break
                                fi
                                sleep 10
                            done

                            echo "📋 Final pod status:"
                            kubectl get pods -n face-recognition

                            echo "📄 Describing non-running pods (if any):"
                            kubectl get pods -n face-recognition | grep -v NAME | grep -v Running | awk '{print $1}' | xargs -I {} kubectl describe pod {} -n face-recognition || true

                            echo "📅 Cluster events:"
                            kubectl get events -n face-recognition --sort-by=.lastTimestamp
                        '''

                        echo '🌐 Exposing frontend service...'
                        sh '''
                            nohup minikube tunnel > /dev/null 2>&1 &
                            sleep 5
                            NODE_PORT=$(kubectl get service frontend -n face-recognition -o=jsonpath="{.spec.ports[0].nodePort}")
                            NODE_IP=$(minikube ip)
                            echo "✅ Access your app at: http://$NODE_IP:$NODE_PORT"
                        '''

                        echo '✅ Kubernetes deployment completed successfully!'

                    } catch (Exception e) {
                        echo "❌ Deployment failed: ${e.getMessage()}"
                        currentBuild.result = 'UNSTABLE'
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
