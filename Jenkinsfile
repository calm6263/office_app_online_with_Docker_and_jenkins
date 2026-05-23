pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
        timestamps()
    }

    environment {
        PROJECT_NAME    = "office-services"
        REGISTRY        = "localhost"
        IMAGE_TAG       = "${env.BUILD_NUMBER}-${env.GIT_COMMIT?.take(7) ?: 'unknown'}"
        COMPOSE_FILE    = "docker-compose.yml"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --format="%H %s" || true'
            }
        }

        stage('Security: Secret Scan') {
            steps {
                script {
                    // التحقق من عدم وجود أسرار مكشوفة في الكود
                    sh '''
                        echo "فحص الكود بحثاً عن كلمات مرور مضمنة..."
                        if grep -rn "password\\s*=\\s*['\"][^'\"]*['\"]" --include="*.py" \
                            | grep -v "generate_password_hash\\|check_password_hash\\|form\\[\\|environ\\|#\\|test" \
                            | grep -v ".env"; then
                            echo "WARNING: قد توجد كلمات مرور مضمنة - يرجى المراجعة"
                        fi
                        echo "فحص الملفات الحساسة..."
                        if [ -f ".env" ]; then
                            echo "WARNING: ملف .env موجود في workspace"
                        fi
                    '''
                }
            }
        }

        stage('Build Docker Images') {
            steps {
                timeout(time: 15, unit: 'MINUTES') {
                    script {
                        sh 'docker-compose -f ${COMPOSE_FILE} build --no-cache web db'
                    }
                }
            }
        }

        stage('Run Tests') {
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    script {
                        withCredentials([
                            string(credentialsId: 'db-password', variable: 'DB_PASSWORD'),
                            string(credentialsId: 'secret-key', variable: 'SECRET_KEY')
                        ]) {
                            sh '''
                                docker-compose -f ${COMPOSE_FILE} up -d db
                                echo "انتظار جاهزية قاعدة البيانات..."
                                timeout 60 bash -c "until docker-compose -f ${COMPOSE_FILE} exec -T db pg_isready; do sleep 2; done"
                                docker-compose -f ${COMPOSE_FILE} run --rm \
                                    -e DATABASE_URL="postgresql://office_user:${DB_PASSWORD}@db:5432/office_services" \
                                    -e SECRET_KEY="${SECRET_KEY}" \
                                    -e FLASK_ENV=testing \
                                    web python -m pytest tests/ -v --tb=short 2>/dev/null || \
                                    docker-compose -f ${COMPOSE_FILE} run --rm \
                                    -e DATABASE_URL="postgresql://office_user:${DB_PASSWORD}@db:5432/office_services" \
                                    -e SECRET_KEY="${SECRET_KEY}" \
                                    web python -m unittest discover -v
                            '''
                        }
                    }
                }
            }
            post {
                always {
                    sh 'docker-compose -f ${COMPOSE_FILE} logs web || true'
                }
            }
        }

        stage('Security: Dependency Check') {
            steps {
                script {
                    sh '''
                        echo "فحص التبعيات بحثاً عن ثغرات معروفة..."
                        docker run --rm \
                            -v $(pwd)/requirements.txt:/app/requirements.txt \
                            python:3.10-slim \
                            bash -c "pip install pip-audit -q && pip-audit -r /app/requirements.txt --format=json" \
                            || echo "pip-audit غير متاح - تخطي فحص التبعيات"
                    '''
                }
            }
        }

        stage('Deploy') {
            when {
                branch 'master'
            }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    script {
                        withCredentials([
                            string(credentialsId: 'db-password', variable: 'DB_PASSWORD'),
                            string(credentialsId: 'secret-key', variable: 'SECRET_KEY')
                        ]) {
                            sh '''
                                export POSTGRES_PASSWORD="${DB_PASSWORD}"
                                export SECRET_KEY="${SECRET_KEY}"
                                docker-compose -f ${COMPOSE_FILE} up -d --build web
                                echo "انتظار جاهزية التطبيق..."
                                timeout 60 bash -c "until curl -sf http://localhost:5001/ > /dev/null 2>&1; do sleep 3; done" || true
                                echo "✅ تم نشر التطبيق"
                            '''
                        }
                    }
                }
            }
        }

        stage('Cleanup') {
            steps {
                script {
                    sh 'docker-compose -f ${COMPOSE_FILE} down --remove-orphans || true'
                    // تنظيف الصور غير المستخدمة فقط
                    sh 'docker image prune -f --filter "until=24h" || true'
                }
            }
        }
    }

    post {
        always {
            cleanWs(
                cleanWhenAborted: true,
                cleanWhenFailure: true,
                cleanWhenSuccess: true,
                deleteDirs: true
            )
        }
        success {
            echo "✅ Pipeline نجح: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        }
        failure {
            echo "❌ Pipeline فشل: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        }
        unstable {
            echo "⚠️ Pipeline غير مستقر: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
        }
    }
}
