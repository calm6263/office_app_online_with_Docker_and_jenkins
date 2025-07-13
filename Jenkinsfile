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
                sh 'docker compose -f docker-compose.yml -f docker-compose.jenkins.yml build'
            }
        }
        
        stage('Run') {
            steps {
                sh 'docker compose -f docker-compose.yml -f docker-compose.jenkins.yml up -d'
            }
        }
        
        stage('Health Check') {
            steps {
                // إضافة خطوات فحص الصحة هنا
            }
        }
    }
    
    post {
        always {
            sh 'docker compose -f docker-compose.yml -f docker-compose.jenkins.yml down -v'
        }
    }
}