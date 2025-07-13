pipeline {
    agent any

    environment {
        DOCKER_REGISTRY = 'docker-registry:5000'
        PROJECT_NAME = 'office-services'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/your-username/your-repo.git'
            }
        }

        stage('Build & Push Docker Images') {
            steps {
                script {
                    docker.build("${PROJECT_NAME}-web:latest", "-f Dockerfile .").push()
                }
            }
        }

        stage('Deploy to Staging') {
            steps {
                sh 'docker-compose down || true'
                sh 'docker-compose up -d --build'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'docker-compose exec -T web python -m pytest tests/'
            }
        }
    }

    post {
        always {
            junit 'tests/results/*.xml'
            cleanWs()
        }
        success {
            slackSend channel: '#deployments', message: "✅ النشر الناجح: ${env.BUILD_URL}"
        }
        failure {
            slackSend channel: '#errors', message: "❌ فشل النشر: ${env.BUILD_URL}"
        }
    }
}