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
                sh 'sleep 30'  # انتظار حتى تبدأ الحاويات
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    // فحص حالة حاوية الويب
                    def webStatus = sh(
                        script: 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml ps -q web',
                        returnStatus: true
                    )
                    
                    if (webStatus != 0) {
                        error "حاوية الويب لم تبدأ بنجاح"
                    }
                    
                    // فحص حالة حاوية قاعدة البيانات
                    def dbStatus = sh(
                        script: 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml exec db pg_isready -U user',
                        returnStatus: true
                    )
                    
                    if (dbStatus != 0) {
                        error "قاعدة البيانات غير جاهزة"
                    }
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