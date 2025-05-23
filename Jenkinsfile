pipeline {
    agent any

    environment {
        // Dummy environment variables
        DOCKER_REGISTRY = 'docker.io/aayushi6402'
        IMAGE_NAME1 = 'training'
        IMAGE_TAG = 'latest'
        IMAGE_NAME2 = 'frontend'    
        IMAGE_NAME3 = 'recognition'
        }

    stages {
        stage('Checkout') {
             steps {
                    echo '📥 Cloning repository...'
                     git url: 'https://github.com/AayushiPrajapati/realtimeFaceRecg.git', branch: 'main'
                }
        }


        stage('Install Dependencies') {
            steps {
                echo '🔧 Installing dependencies...'
                sh 'pip install -r requirements.txt'
            }
        }

        stage('Build Docker Images') {
            steps {
                echo '🐳 Building Docker image...'
                sh 'echo docker build -t $DOCKER_REGISTRY/$IMAGE_NAME:latest .'
            }
        }

        stage('Push Docker Images') {
            steps {
                echo '📦 Pushing Docker image to registry...'
                sh 'echo docker push $DOCKER_REGISTRY/$IMAGE_NAME:latest'
            }
        }

        stage('Run Tests') {
            steps {
                echo '🧪 Running dummy tests...'
                sh 'echo pytest tests/ || true'
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo '🚀 Deploying to Kubernetes...'
                // sh 'bash kubernetes_start.sh'
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
