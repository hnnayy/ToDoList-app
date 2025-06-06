pipeline {
    agent any
    
    environment {
        VENV = 'venv'
        BANDIT_REPORT = 'bandit_report.txt'
        ZAP_REPORT = 'zap_report.html'
        APP_URL = 'http://localhost:5000'
    }
    
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', credentialsId: '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', url: 'https://github.com/hnnayy/ToDoList-app.git'
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
                
                // Check for critical vulnerabilities
                script {
                    def banditOutput = readFile(BANDIT_REPORT)
                    if (banditOutput.contains('High: [1-9]')) {
                        error("Critical security vulnerabilities found in SAST scan!")
                    }
                }
            }
        }
        
        stage('Deploy to Staging') {
            steps {
                echo 'Running docker-compose up...'
                sh 'docker-compose up -d --build'
                
                // Wait for app to be ready
                sleep 30
                
                // Health check
                script {
                    def response = sh(script: "curl -f $APP_URL || echo 'failed'", returnStdout: true).trim()
                    if (response == 'failed') {
                        error("Application failed to start properly!")
                    }
                }
            }
        }
        
        stage('DAST Final Scan') {
            steps {
                echo 'Running DAST scan on deployed application...'
                
                // Install OWASP ZAP
                sh '''
                    if ! command -v zap-baseline.py &> /dev/null; then
                        echo "Installing OWASP ZAP..."
                        wget -q https://github.com/zaproxy/zaproxy/releases/download/v2.14.0/ZAP_2.14.0_Linux.tar.gz
                        tar -xzf ZAP_2.14.0_Linux.tar.gz
                        export PATH=$PATH:$(pwd)/ZAP_2.14.0
                    fi
                '''
                
                // Run ZAP baseline scan
                script {
                    def zapResult = sh(
                        script: "zap-baseline.py -t $APP_URL -J $ZAP_REPORT || echo 'ZAP_SCAN_FAILED'", 
                        returnStdout: true
                    ).trim()
                    
                    // Archive ZAP report
                    archiveArtifacts artifacts: "$ZAP_REPORT", allowEmptyArchive: true, fingerprint: true
                    
                    // Check for critical vulnerabilities
                    if (zapResult.contains('ZAP_SCAN_FAILED')) {
                        def zapReport = readFile(ZAP_REPORT)
                        if (zapReport.contains('"risk": "High"')) {
                            error("Critical security vulnerabilities found in DAST scan! Deployment blocked.")
                        }
                    }
                }
                
                echo 'DAST scan completed - No critical vulnerabilities found'
            }
        }
        
        stage('Deploy to Production') {
            when {
                expression { currentBuild.result == null || currentBuild.result == 'SUCCESS' }
            }
            steps {
                echo 'All security checks passed!'
                echo 'Ready for production deployment...'
                
                // Placeholder for actual production deployment
                // sh 'kubectl apply -f k8s-manifests/'
                // atau
                // sh 'docker-compose -f docker-compose.prod.yml up -d'
            }
        }
    }
    
    post {
        always {
            junit allowEmptyResults: true, testResults: '**/test-results.xml'
            
            // Cleanup
            sh 'docker-compose down || true'
        }
        
        failure {
            echo 'Pipeline failed! Check security scan results.'
            emailext (
                subject: "Pipeline Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "The pipeline failed. Please check the security scan results.",
                to: "dev-team@company.com"
            )
        }
        
        success {
            echo 'Pipeline completed successfully!'
        }
    }
}
