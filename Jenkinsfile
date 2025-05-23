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
                sh 'cp -r /var/jenkins_data/data ./data'
                sh 'cp -r /var/jenkins_data/models ./models'
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
                sh '''
                    minikube delete || true
                    minikube start --driver=docker --cpus=4 --memory=4096 --force

                    minikube status

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
                    kubectl apply -f k8s/training-deployment.yaml
                    kubectl apply -f k8s/services.yaml

                    kubectl get pods -n face-recognition
                    kubectl get services -n face-recognition

                    minikube service frontend-service -n face-recognition --url

                    kubectl logs -n face-recognition -l app=recognition --tail=20
                    kubectl logs -n face-recognition -l app=frontend --tail=20
                    kubectl logs -n face-recognition -l app=training --tail=20
                '''
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
