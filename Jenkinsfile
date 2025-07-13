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
                sh 'docker-compose -f docker-compose.yml build'
            }
        }
        
        stage('Run') {
            steps {
                sh 'docker-compose -f docker-compose.yml up -d'
                sh 'sleep 30'  // Wait for containers to start
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    // Verify Docker installation
                    sh 'docker --version'
                    sh 'docker-compose --version'
                    
                    // Check web container status
                    def webStatus = sh(
                        script: 'docker-compose -f docker-compose.yml ps -q web',
                        returnStatus: true
                    )
                    
                    if (webStatus != 0) {
                        error "Web container failed to start"
                    }
                    
                    // Check database readiness
                    def dbStatus = sh(
                        script: 'docker-compose -f docker-compose.yml exec db pg_isready -U user',
                        returnStatus: true
                    )
                    
                    if (dbStatus != 0) {
                        error "Database is not ready"
                    }
                }
            }
        }
    }
    
    post {
        always {
            sh 'docker-compose -f docker-compose.yml down -v'
        }
    }
}