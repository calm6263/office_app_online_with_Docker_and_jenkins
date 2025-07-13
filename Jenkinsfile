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
                // تم إضافة خطوة فحص الصحة الأساسية
                script {
                    timeout(time: 1, unit: 'MINUTES') {
                        waitUntil {
                            def status = sh(
                                script: 'docker compose -f docker-compose.yml -f docker-compose.jenkins.yml ps --services --filter "status=running"',
                                returnStatus: true
                            )
                            return status == 0
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            sh 'docker compose -f docker-compose.yml -f docker-compose.jenkins.yml down -v'
        }
    }
}