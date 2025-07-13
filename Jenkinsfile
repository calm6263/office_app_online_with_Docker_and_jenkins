pipeline {
    agent {
        docker {
            image 'python:3.10'
            args '-v /var/run/docker.sock:/var/run/docker.sock'
        }
    }
    
    environment {
        DOCKER_COMPOSE = 'docker-compose'
        PROJECT_NAME = 'office-services'
    }
    
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/yourusername/your-repo.git'
            }
        }
        
        stage('Build') {
            steps {
                sh 'pip install -r requirements.txt'
                sh 'docker-compose build'
            }
        }
        
        stage('Test') {
            steps {
                sh 'python -m pytest tests/'
            }
        }
        
        stage('Deploy') {
            steps {
                sh 'docker-compose up -d'
            }
        }
    }
    
    post {
        always {
            sh 'docker-compose down'
        }
        success {
            slackSend channel: '#deployments', message: 'Deployment succeeded!'
        }
        failure {
            slackSend channel: '#errors', message: 'Deployment failed!'
        }
    }
}