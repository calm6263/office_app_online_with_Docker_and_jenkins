pipeline {
<<<<<<< HEAD
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
=======
    agent any

    environment {
        DOCKER_COMPOSE = 'docker-compose'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', url: 'https://github.com/yourusername/yourrepo.git'
            }
        }

        stage('Build and Test') {
            steps {
                sh 'docker-compose build'
                sh 'docker-compose run web python -m pytest tests/'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker-compose down'
                sh 'docker-compose up -d --build'
            }
        }

        stage('Run Migrations') {
            steps {
                sh 'while ! docker-compose exec db pg_isready -U user; do sleep 5; done'
                sh 'docker-compose exec web python -c "from app import db; db.create_all()"'
            }
        }
    }

    post {
        always {
            junit 'tests/results/*.xml'
        }
        success {
            slackSend channel: '#deployments', message: "Deployment succeeded: ${env.BUILD_URL}"
        }
        failure {
            slackSend channel: '#errors', message: "Deployment failed: ${env.BUILD_URL}"
>>>>>>> 71228168046667e5ed08ebad6ebd7472f5ee1064
        }
    }
}