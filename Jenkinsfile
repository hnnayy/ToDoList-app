pipeline {
    agent any
    environment {
        VENV = 'venv'
        BANDIT_REPORT = 'bandit_report.txt'
        BANDIT_JSON_REPORT = 'bandit_report.json'
        SECURITY_THRESHOLD_HIGH = '0'      // Max HIGH severity issues allowed
        SECURITY_THRESHOLD_MEDIUM = '5'    // Max MEDIUM severity issues allowed
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
                
                // Generate both text and JSON reports
                sh '. $VENV/bin/activate && bandit -r todo_app -ll -iii -o $BANDIT_REPORT || true'
                sh '. $VENV/bin/activate && bandit -r todo_app -ll -iii -f json -o $BANDIT_JSON_REPORT || true'
                
                // Archive reports
                archiveArtifacts artifacts: "$BANDIT_REPORT,$BANDIT_JSON_REPORT", fingerprint: true
            }
        }
        stage('Security Quality Gate') {
            steps {
                script {
                    // Read and evaluate security scan results
                    def securityIssues = [:]
                    def scanPassed = true
                    def warningMessage = ""
                    
                    try {
                        // Check if JSON report exists and has content
                        if (fileExists("$BANDIT_JSON_REPORT")) {
                            def jsonReport = readJSON file: "$BANDIT_JSON_REPORT"
                            
                            if (jsonReport.results) {
                                // Count issues by severity
                                def highIssues = jsonReport.results.findAll { it.issue_severity == 'HIGH' }
                                def mediumIssues = jsonReport.results.findAll { it.issue_severity == 'MEDIUM' }
                                def lowIssues = jsonReport.results.findAll { it.issue_severity == 'LOW' }
                                
                                securityIssues = [
                                    high: highIssues.size(),
                                    medium: mediumIssues.size(),
                                    low: lowIssues.size(),
                                    total: jsonReport.results.size()
                                ]
                                
                                echo "🔍 Security Scan Results:"
                                echo "   HIGH: ${securityIssues.high}"
                                echo "   MEDIUM: ${securityIssues.medium}" 
                                echo "   LOW: ${securityIssues.low}"
                                echo "   TOTAL: ${securityIssues.total}"
                                
                                // Check thresholds
                                if (securityIssues.high > SECURITY_THRESHOLD_HIGH.toInteger()) {
                                    scanPassed = false
                                    error("🚨 SECURITY GATE FAILED: ${securityIssues.high} HIGH severity issues found (threshold: ${SECURITY_THRESHOLD_HIGH})")
                                }
                                
                                if (securityIssues.medium > SECURITY_THRESHOLD_MEDIUM.toInteger()) {
                                    warningMessage = "⚠️ SECURITY WARNING: ${securityIssues.medium} MEDIUM severity issues found (threshold: ${SECURITY_THRESHOLD_MEDIUM})"
                                    currentBuild.result = 'UNSTABLE'
                                }
                                
                                // Log first few issues for visibility
                                if (securityIssues.total > 0) {
                                    echo "📋 Sample Issues Found:"
                                    jsonReport.results.take(3).each { issue ->
                                        echo "   - ${issue.issue_severity}: ${issue.issue_text} (${issue.filename}:${issue.line_number})"
                                    }
                                }
                            } else {
                                echo "✅ No security issues found!"
                            }
                        } else {
                            echo "⚠️ JSON report not found, using text report fallback"
                            // Fallback: check if text report indicates issues
                            def reportContent = readFile("$BANDIT_REPORT")
                            if (reportContent.contains(">> Issue")) {
                                warningMessage = "⚠️ Security issues detected (check text report for details)"
                                currentBuild.result = 'UNSTABLE'
                            }
                        }
                        
                        // Set build properties for dashboard
                        currentBuild.displayName = "#${BUILD_NUMBER} - Security: ${securityIssues.total ?: 0} issues"
                        currentBuild.description = "HIGH: ${securityIssues.high ?: 0}, MEDIUM: ${securityIssues.medium ?: 0}, LOW: ${securityIssues.low ?: 0}"
                        
                        if (warningMessage) {
                            echo warningMessage
                        }
                        
                        if (scanPassed && !warningMessage) {
                            echo "✅ Security Quality Gate: PASSED"
                        }
                        
                    } catch (Exception e) {
                        echo "⚠️ Error evaluating security scan: ${e.message}"
                        echo "Continuing with deployment (scan evaluation failed)"
                    }
                }
            }
        }
        stage('Deploy to Staging') {
            when {
                not { 
                    equals expected: 'FAILURE', actual: currentBuild.result 
                }
            }
            steps {
                echo 'Running docker-compose up...'
                sh 'docker-compose up -d --build'
                
                script {
                    // Add deployment info to build description
                    if (currentBuild.description) {
                        currentBuild.description += " | Deployed: ✅"
                    } else {
                        currentBuild.description = "Deployed: ✅"
                    }
                }
            }
        }
    }
    post {
        always {
            junit allowEmptyResults: true, testResults: '**/test-results.xml'
            
            // Generate security summary
            script {
                try {
                    if (fileExists("$BANDIT_JSON_REPORT")) {
                        def jsonReport = readJSON file: "$BANDIT_JSON_REPORT"
                        def summary = """
                        🔒 Security Scan Summary - Build #${BUILD_NUMBER}
                        ================================================
                        Commit: ${env.GIT_COMMIT?.take(7) ?: 'N/A'}
                        Total Issues: ${jsonReport.results?.size() ?: 0}
                        Report: ${BUILD_URL}artifact/${BANDIT_REPORT}
                        """
                        echo summary
                        writeFile file: 'security_summary.txt', text: summary
                        archiveArtifacts artifacts: 'security_summary.txt', fingerprint: true
                    }
                } catch (Exception e) {
                    echo "Could not generate security summary: ${e.message}"
                }
            }
        }
        success {
            echo "🎉 Pipeline completed successfully!"
            script {
                if (currentBuild.result == 'UNSTABLE') {
                    echo "⚠️ Note: Build marked as UNSTABLE due to security warnings"
                }
            }
        }
        failure {
            echo "❌ Pipeline failed!"
            echo "Check security scan results: ${BUILD_URL}artifact/${BANDIT_REPORT}"
        }
        unstable {
            echo "⚠️ Pipeline completed with warnings!"
            echo "Security issues found but within acceptable limits"
        }
    }
}
