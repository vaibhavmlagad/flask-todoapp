pipeline {

    agent none

    options {
        timestamps()
        ansiColor('xterm')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
        timeout(time: 45, unit: 'MINUTES')
    }

    parameters {
        choice(
            name: 'DEPLOY_ENV',
            choices: ['none', 'staging', 'production'],
            description: 'Environment to deploy to after a successful build. "none" skips deployment (build/test only).'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: 'Skip the unit test stage (use only for emergency hotfix builds).'
        )
        booleanParam(
            name: 'FORCE_IMAGE_SCAN',
            defaultValue: true,
            description: 'Run the Trivy vulnerability scan on the built image.'
        )
    }

    environment {
        // ---- Registry / image settings ----
        REGISTRY         = 'docker.io/vaibhavlagad'
        IMAGE_NAME       = "${REGISTRY}/todo-app"
        REGISTRY_CRED_ID = 'dockerhub-creds'

        // ---- Kubernetes settings ----
        K8S_NAMESPACE  = 'todo-app'
        K8S_DEPLOYMENT = 'todo-app'
        K8S_CONTAINER  = 'todo-app'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_SHORT_SHA  = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG      = "${env.BUILD_NUMBER}-${env.GIT_SHORT_SHA}"
                    env.GIT_COMMIT_MSG = sh(script: 'git log -1 --pretty=%s', returnStdout: true).trim()
                }
                echo "Building ${IMAGE_NAME}:${env.IMAGE_TAG} — ${env.GIT_COMMIT_MSG}"

                // Since every later stage gets its own agent/workspace,
                // stash the checked-out source so those stages can unstash it.
                stash name: 'source', includes: '**/*', excludes: '.git/**'
            }
        }

        stage('Lint') {
            agent { docker { image 'python:3.12-slim' } }
            steps {
                unstash 'source'
                sh '''
                    pip install --no-cache-dir --quiet flake8
                    echo "Running flake8 static analysis..."
                    flake8 app.py --max-line-length=120 --statistics --tee --output-file=flake8-report.txt || true
                '''
                archiveArtifacts artifacts: 'flake8-report.txt', allowEmptyArchive: true
            }
        }

        stage('Unit Tests') {
            when { expression { return !params.SKIP_TESTS } }
            agent { docker { image 'python:3.12-slim' } }
            steps {
                unstash 'source'
                sh '''
                    pip install --no-cache-dir --quiet -r requirements.txt
                    pip install --no-cache-dir --quiet pytest pytest-cov
                    mkdir -p reports
                    pytest tests/ -v \
                        --junitxml=reports/junit.xml \
                        --cov=app --cov-report=xml:reports/coverage.xml --cov-report=term
                '''
            }
            post {
                always {
                    junit testResults: 'reports/junit.xml', allowEmptyResults: true
                    archiveArtifacts artifacts: 'reports/*.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Build Image') {
            steps {
                unstash 'source'
                sh '''
                    docker build \
                        --pull \
                        --label org.opencontainers.image.revision=$GIT_SHORT_SHA \
                        --label org.opencontainers.image.version=$IMAGE_TAG \
                        -t $IMAGE_NAME:$IMAGE_TAG \
                        -t $IMAGE_NAME:latest \
                        .
                '''
            }
        }

        stage('Scan Image') {
            when { expression { return params.FORCE_IMAGE_SCAN } }
            agent { docker { image 'aquasec/trivy:latest' } }
            steps {
                sh '''
                    mkdir -p trivy-report
                    trivy image \
                        --severity HIGH,CRITICAL \
                        --exit-code 0 \
                        --format table \
                        -o trivy-report/trivy-report.txt \
                        $IMAGE_NAME:$IMAGE_TAG || true
                '''
                archiveArtifacts artifacts: 'trivy-report/*.txt', allowEmptyArchive: true
            }
        }

        stage('Push Image') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                    expression { return params.DEPLOY_ENV != 'none' }
                }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: env.REGISTRY_CRED_ID,
                    usernameVariable: 'REG_USER',
                    passwordVariable: 'REG_PASS'
                )]) {
                    sh '''
                        echo "$REG_PASS" | docker login "$REGISTRY" -u "$REG_USER" --password-stdin
                        docker push "$IMAGE_NAME:$IMAGE_TAG"
                        docker push "$IMAGE_NAME:latest"
                        docker logout || true
                    '''
                }
            }
        }

        stage('Deploy') {
            when { expression { return params.DEPLOY_ENV != 'none' } }
            agent {
                docker {
                    image 'bitnami/kubectl:latest'
                    args "--entrypoint=''"
                }
            }
            steps {
                unstash 'source' // k8s/ manifests come from the repo
                script {
                    def kubeconfigCred = params.DEPLOY_ENV == 'production' ? 'kubeconfig-prod' : 'kubeconfig-staging'
                    withCredentials([file(credentialsId: kubeconfigCred, variable: 'KUBECONFIG')]) {
                        sh """
                            echo "Deploying ${IMAGE_NAME}:${env.IMAGE_TAG} to ${params.DEPLOY_ENV} (namespace: ${K8S_NAMESPACE})"

                            kubectl apply -k k8s/

                            kubectl -n ${K8S_NAMESPACE} set image \
                                deployment/${K8S_DEPLOYMENT} \
                                ${K8S_CONTAINER}=${IMAGE_NAME}:${env.IMAGE_TAG} \
                                --record

                            kubectl -n ${K8S_NAMESPACE} rollout status \
                                deployment/${K8S_DEPLOYMENT} \
                                --timeout=180s
                        """
                    }
                }
            }
        }

        stage('Smoke Test') {
            when { expression { return params.DEPLOY_ENV != 'none' } }
            agent {
                docker {
                    image 'bitnami/kubectl:latest'
                    args "--entrypoint=''"
                }
            }
            steps {
                script {
                    def kubeconfigCred = params.DEPLOY_ENV == 'production' ? 'kubeconfig-prod' : 'kubeconfig-staging'
                    withCredentials([file(credentialsId: kubeconfigCred, variable: 'KUBECONFIG')]) {
                        sh """
                            kubectl -n ${K8S_NAMESPACE} run smoke-test-${BUILD_NUMBER} \
                                --rm -i --restart=Never \
                                --image=curlimages/curl:latest -- \
                                curl -sf http://todo-app-service.${K8S_NAMESPACE}.svc.cluster.local/healthz
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            echo "✅ Build #${BUILD_NUMBER} succeeded — image ${IMAGE_NAME}:${env.IMAGE_TAG}"
        }
        failure {
            echo "❌ Build #${BUILD_NUMBER} failed. Check stage logs above."
        }
        unstable {
            echo "⚠️ Build #${BUILD_NUMBER} completed with test/lint issues — review reports."
        }
        always {
            node() {
                sh 'docker image prune -f --filter "until=72h" || true'
                cleanWs()
            }
        }
    }
}