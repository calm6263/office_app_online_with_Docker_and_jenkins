pipeline {
    agent any

    environment {
        PROJECT_NAME = "office-services"
    }

    stages {
        stage('Build Docker Images') {
            steps {
                script {
                    sh 'docker-compose build --no-cache'
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    sh 'docker-compose up -d db'
                    sh 'sleep 10'
                    sh 'docker-compose run --rm web python -m unittest discover'
                }
            }
        }
        
        stage('Deploy Application') {
            steps {
                script {
                    sh 'docker-compose up -d --build web'
                }
            }
        }
        
        stage('Cleanup') {
            steps {
                script {
                    sh 'docker system prune -f'
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            slackSend(color: "good", message: "Build succeeded: ${env.JOB_NAME} #${env.BUILD_NUMBER}")
        }
        failure {
            slackSend(color: "danger", message: "Build failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}")
        }
    }
}