pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml build'
            }
        }
        
        stage('Run') {
            steps {
                sh 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml up -d'
            }
        }
        
        stage('Health Check') {
            steps {
                script {
                    waitUntil {
                        def status = sh(
                            script: 'docker inspect --format="{{.State.Health.Status}}" office_app-web-1',
                            returnStdout: true
                        ).trim()
                        return status == 'healthy'
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