pipeline {
    agent any
    environment {
        DOCKER_COMPOSE = 'docker-compose -f docker-compose.yml -f docker-compose.jenkins.yml'
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Build & Run') {
            steps {
                script {
                    sh "${DOCKER_COMPOSE} build --pull"
                    sh "${DOCKER_COMPOSE} up -d --force-recreate"
                }
            }
        }
        stage('Health Check') {
            steps {
                script {
                    timeout(time: 5, unit: 'MINUTES') {
                        waitUntil {
                            try {
                                sh 'curl -sSf http://localhost:5000 > /dev/null'
                                return true
                            } catch (Exception e) {
                                return false
                            }
                        }
                    }
                }
            }
        }
        stage('Test') {
            steps {
                script {
                    sh "${DOCKER_COMPOSE} exec web python -m pytest tests/"
                }
            }
        }
    }
    post {
        always {
            script {
                sh "${DOCKER_COMPOSE} down -v --remove-orphans"
            }
        }
    }
}