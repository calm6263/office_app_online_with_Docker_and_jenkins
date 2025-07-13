pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Build') {
            steps {
                sh 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml build'
            }
        }
        
        stage('Run') {
            steps {
                sh 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml up -d'
                sh 'sleep 30'  // Wait for containers to start
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    // Verify Docker installation inside Jenkins container
                    sh 'docker --version'
                    sh 'docker-compose --version'
                    
                    // Check web container status
                    sh 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml ps'
                }
            }
        }
    }
    
    post {
        always {
            sh 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml down -v'
        }
    }
}