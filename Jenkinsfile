pipeline {
    agent any

    environment {
        VENV = 'venv'
        BANDIT_REPORT = 'bandit_report.txt'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', credentialsId: 'github-token', url: 'https://github.com/hnnayy/ToDoList-app.git'
            }
        }

        stage('Build') {
            steps {
                sh 'python3 -m venv $VENV'
                sh '. $VENV/bin/activate && pip install -r requirements.txt'
            }
        }

        stage('Unit Test') {
            steps {
                sh '. $VENV/bin/activate && python3 -m unittest discover tests'
            }
        }

        stage('Security Scan (Bandit)') {
            steps {
                sh '. $VENV/bin/activate && pip install bandit'
                sh '. $VENV/bin/activate && bandit -r todo_app -ll -iii -o $BANDIT_REPORT || true'
                archiveArtifacts artifacts: "$BANDIT_REPORT", fingerprint: true
            }
        }

        stage('Deploy to Staging') {
            steps {
                echo 'Running docker-compose up...'
                sh 'docker-compose up -d --build'
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: '**/test-results.xml'
        }
    }
}
