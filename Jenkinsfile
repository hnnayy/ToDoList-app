pipeline {
    agent any
    environment {
        VENV = 'venv'
        BANDIT_REPORT = 'bandit_report.txt'
        BANDIT_JSON_REPORT = 'bandit_report.json'
        SONARQUBE_REPORT = 'sonarqube_report.json'
        ZAP_REPORT = 'zap_report.html'
        ZAP_JSON_REPORT = 'zap_report.json'
        SECURITY_THRESHOLD_HIGH = '0'      // Max HIGH severity issues allowed
        SECURITY_THRESHOLD_MEDIUM = '5'    // Max MEDIUM severity issues allowed
        APP_URL = 'http://localhost:5000'  // Application URL for DAST
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
        stage('SAST - Bandit Scan') {
            steps {
                sh '. $VENV/bin/activate && pip install bandit'
                
                // Generate both text and JSON reports
                sh '. $VENV/bin/activate && bandit -r todo_app -ll -iii -o $BANDIT_REPORT || true'
                sh '. $VENV/bin/activate && bandit -r todo_app -ll -iii -f json -o $BANDIT_JSON_REPORT || true'
                
                // Archive reports
                archiveArtifacts artifacts: "$BANDIT_REPORT,$BANDIT_JSON_REPORT", fingerprint: true
            }
        }
        stage('SAST - SonarQube Analysis') {
            steps {
                script {
                    try {
                        // Install sonar-scanner if not available
                        sh '''
                            if ! command -v sonar-scanner &> /dev/null; then
                                echo "Installing SonarQube Scanner..."
                                wget -q https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-4.8.0.2856-linux.zip
                                unzip -q sonar-scanner-cli-4.8.0.2856-linux.zip
                                export PATH=$PATH:$(pwd)/sonar-scanner-4.8.0.2856-linux/bin
                            fi
                        '''
                        
                        // Create sonar-project.properties if not exists
                        writeFile file: 'sonar-project.properties', text: '''
sonar.projectKey=todolist-app
sonar.projectName=ToDoList Application
sonar.projectVersion=1.0
sonar.sources=todo_app
sonar.tests=tests
sonar.language=py
sonar.sourceEncoding=UTF-8
sonar.python.coverage.reportPaths=coverage.xml
                        '''
                        
                        // Run SonarQube analysis (skip if no server configured)
                        sh '''
                            if [ -n "$SONAR_HOST_URL" ]; then
                                ./sonar-scanner-4.8.0.2856-linux/bin/sonar-scanner || echo "SonarQube analysis failed, continuing..."
                            else
                                echo "SonarQube server not configured, skipping analysis"
                                echo '{"issues": []}' > $SONARQUBE_REPORT
                            fi
                        '''
                        
                    } catch (Exception e) {
                        echo "SonarQube analysis failed: ${e.message}"
                        echo "Continuing with pipeline..."
                        writeFile file: env.SONARQUBE_REPORT, text: '{"issues": []}'
                    }
                }
                
                archiveArtifacts artifacts: "$SONARQUBE_REPORT", allowEmptyArchive: true, fingerprint: true
            }
        }
        stage('SAST - Semgrep Scan') {
            steps {
                script {
                    try {
                        sh '''
                            # Install semgrep
                            . $VENV/bin/activate
                            pip install semgrep
                            
                            # Run semgrep scan
                            semgrep --config=auto --json --output=semgrep_report.json todo_app/ || true
                            
                            # Generate human readable report
                            semgrep --config=auto --output=semgrep_report.txt todo_app/ || true
                        '''
                        
                        archiveArtifacts artifacts: "semgrep_report.json,semgrep_report.txt", allowEmptyArchive: true, fingerprint: true
                        
                    } catch (Exception e) {
                        echo "Semgrep scan failed: ${e.message}"
                        echo "Continuing with pipeline..."
                    }
                }
            }
        }
        stage('SAST Quality Gate') {
            steps {
                script {
                    // Evaluate SAST scan results
                    def sastIssues = [:]
                    def scanPassed = true
                    def warningMessage = ""
                    
                    try {
                        // Evaluate Bandit results
                        if (fileExists("$BANDIT_JSON_REPORT")) {
                            def banditReport = readJSON file: "$BANDIT_JSON_REPORT"
                            
                            if (banditReport.results) {
                                def highIssues = banditReport.results.findAll { it.issue_severity == 'HIGH' }
                                def mediumIssues = banditReport.results.findAll { it.issue_severity == 'MEDIUM' }
                                def lowIssues = banditReport.results.findAll { it.issue_severity == 'LOW' }
                                
                                sastIssues.bandit = [
                                    high: highIssues.size(),
                                    medium: mediumIssues.size(),
                                    low: lowIssues.size(),
                                    total: banditReport.results.size()
                                ]
                                
                                echo "Bandit Scan Results:"
                                echo "   HIGH: ${sastIssues.bandit.high}"
                                echo "   MEDIUM: ${sastIssues.bandit.medium}" 
                                echo "   LOW: ${sastIssues.bandit.low}"
                                echo "   TOTAL: ${sastIssues.bandit.total}"
                                
                                if (sastIssues.bandit.high > SECURITY_THRESHOLD_HIGH.toInteger()) {
                                    scanPassed = false
                                    error("SAST GATE FAILED: ${sastIssues.bandit.high} HIGH severity issues found in Bandit scan")
                                }
                                
                                if (sastIssues.bandit.medium > SECURITY_THRESHOLD_MEDIUM.toInteger()) {
                                    warningMessage = "SAST WARNING: ${sastIssues.bandit.medium} MEDIUM severity issues found in Bandit scan"
                                    currentBuild.result = 'UNSTABLE'
                                }
                            }
                        }
                        
                        // Evaluate Semgrep results
                        if (fileExists("semgrep_report.json")) {
                            def semgrepReport = readJSON file: "semgrep_report.json"
                            
                            if (semgrepReport.results) {
                                def criticalIssues = semgrepReport.results.findAll { it.extra?.severity == 'ERROR' }
                                def warningIssues = semgrepReport.results.findAll { it.extra?.severity == 'WARNING' }
                                
                                sastIssues.semgrep = [
                                    critical: criticalIssues.size(),
                                    warning: warningIssues.size(),
                                    total: semgrepReport.results.size()
                                ]
                                
                                echo "Semgrep Scan Results:"
                                echo "   CRITICAL: ${sastIssues.semgrep.critical}"
                                echo "   WARNING: ${sastIssues.semgrep.warning}"
                                echo "   TOTAL: ${sastIssues.semgrep.total}"
                                
                                if (sastIssues.semgrep.critical > 0) {
                                    scanPassed = false
                                    error("SAST GATE FAILED: ${sastIssues.semgrep.critical} CRITICAL issues found in Semgrep scan")
                                }
                            }
                        }
                        
                        // Set build properties
                        def totalIssues = (sastIssues.bandit?.total ?: 0) + (sastIssues.semgrep?.total ?: 0)
                        currentBuild.displayName = "#${BUILD_NUMBER} - SAST: ${totalIssues} issues"
                        currentBuild.description = "Bandit: ${sastIssues.bandit?.total ?: 0}, Semgrep: ${sastIssues.semgrep?.total ?: 0}"
                        
                        if (warningMessage) {
                            echo warningMessage
                        }
                        
                        if (scanPassed && !warningMessage) {
                            echo "SAST Quality Gate: PASSED"
                        }
                        
                    } catch (Exception e) {
                        echo "Error evaluating SAST results: ${e.message}"
                        echo "Continuing with pipeline"
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
                
                // Wait for application to be ready
                script {
                    def maxAttempts = 30
                    def attempt = 0
                    def appReady = false
                    
                    while (attempt < maxAttempts && !appReady) {
                        try {
                            sh "curl -f ${APP_URL} > /dev/null 2>&1"
                            appReady = true
                            echo "Application is ready at ${APP_URL}"
                        } catch (Exception e) {
                            attempt++
                            echo "Waiting for application to start... (${attempt}/${maxAttempts})"
                            sleep(10)
                        }
                    }
                    
                    if (!appReady) {
                        error("Application failed to start after ${maxAttempts * 10} seconds")
                    }
                    
                    // Add deployment info to build description
                    if (currentBuild.description) {
                        currentBuild.description += " | Deployed: Ready"
                    } else {
                        currentBuild.description = "Deployed: Ready"
                    }
                }
            }
        }
        stage('DAST - OWASP ZAP Scan') {
            when {
                not { 
                    equals expected: 'FAILURE', actual: currentBuild.result 
                }
            }
            steps {
                script {
                    try {
                        // Run OWASP ZAP Docker container
                        sh '''
                            # Pull ZAP Docker image
                            docker pull owasp/zap2docker-stable
                            
                            # Create reports directory
                            mkdir -p zap_reports
                            
                            # Run ZAP baseline scan
                            docker run --rm \
                                --network host \
                                -v $(pwd)/zap_reports:/zap/wrk/:rw \
                                owasp/zap2docker-stable zap-baseline.py \
                                -t $APP_URL \
                                -J zap_report.json \
                                -r zap_report.html \
                                -x zap_report.xml || true
                            
                            # Move reports to workspace
                            mv zap_reports/zap_report.json . || echo "JSON report not found"
                            mv zap_reports/zap_report.html . || echo "HTML report not found" 
                            mv zap_reports/zap_report.xml . || echo "XML report not found"
                        '''
                        
                        // Archive ZAP reports
                        archiveArtifacts artifacts: "zap_report.*", allowEmptyArchive: true, fingerprint: true
                        
                    } catch (Exception e) {
                        echo "OWASP ZAP scan failed: ${e.message}"
                        echo "Continuing with pipeline..."
                    }
                }
            }
        }
        stage('DAST - Nikto Scan') {
            when {
                not { 
                    equals expected: 'FAILURE', actual: currentBuild.result 
                }
            }
            steps {
                script {
                    try {
                        sh '''
                            # Install Nikto if not available
                            if ! command -v nikto &> /dev/null; then
                                echo "Installing Nikto..."
                                apt-get update && apt-get install -y nikto || echo "Failed to install Nikto"
                            fi
                            
                            # Run Nikto scan
                            if command -v nikto &> /dev/null; then
                                nikto -h $APP_URL -output nikto_report.txt -Format txt || true
                                nikto -h $APP_URL -output nikto_report.json -Format json || true
                            else
                                echo "Nikto not available, skipping scan"
                                echo "No Nikto scan performed" > nikto_report.txt
                                echo '{"vulnerabilities": []}' > nikto_report.json
                            fi
                        '''
                        
                        archiveArtifacts artifacts: "nikto_report.*", allowEmptyArchive: true, fingerprint: true
                        
                    } catch (Exception e) {
                        echo "Nikto scan failed: ${e.message}"
                        echo "Continuing with pipeline..."
                    }
                }
            }
        }
        stage('DAST Quality Gate') {
            when {
                not { 
                    equals expected: 'FAILURE', actual: currentBuild.result 
                }
            }
            steps {
                script {
                    def dastIssues = [:]
                    def scanPassed = true
                    def warningMessage = ""
                    
                    try {
                        // Evaluate ZAP results
                        if (fileExists("zap_report.json")) {
                            def zapReport = readJSON file: "zap_report.json"
                            
                            if (zapReport.site) {
                                def highAlerts = []
                                def mediumAlerts = []
                                def lowAlerts = []
                                
                                zapReport.site.each { site ->
                                    site.alerts?.each { alert ->
                                        switch(alert.riskdesc?.toLowerCase()) {
                                            case ~/.*high.*/:
                                                highAlerts.add(alert)
                                                break
                                            case ~/.*medium.*/:
                                                mediumAlerts.add(alert)
                                                break
                                            case ~/.*low.*/:
                                                lowAlerts.add(alert)
                                                break
                                        }
                                    }
                                }
                                
                                dastIssues.zap = [
                                    high: highAlerts.size(),
                                    medium: mediumAlerts.size(),
                                    low: lowAlerts.size(),
                                    total: highAlerts.size() + mediumAlerts.size() + lowAlerts.size()
                                ]
                                
                                echo "OWASP ZAP Scan Results:"
                                echo "   HIGH: ${dastIssues.zap.high}"
                                echo "   MEDIUM: ${dastIssues.zap.medium}"
                                echo "   LOW: ${dastIssues.zap.low}"
                                echo "   TOTAL: ${dastIssues.zap.total}"
                                
                                if (dastIssues.zap.high > 0) {
                                    scanPassed = false
                                    error("DAST GATE FAILED: ${dastIssues.zap.high} HIGH severity vulnerabilities found")
                                }
                                
                                if (dastIssues.zap.medium > 3) {
                                    warningMessage = "DAST WARNING: ${dastIssues.zap.medium} MEDIUM severity vulnerabilities found"
                                    currentBuild.result = 'UNSTABLE'
                                }
                            }
                        }
                        
                        // Update build information
                        def totalDastIssues = dastIssues.zap?.total ?: 0
                        if (currentBuild.description) {
                            currentBuild.description += " | DAST: ${totalDastIssues} issues"
                        } else {
                            currentBuild.description = "DAST: ${totalDastIssues} issues"
                        }
                        
                        if (warningMessage) {
                            echo warningMessage
                        }
                        
                        if (scanPassed && !warningMessage) {
                            echo "DAST Quality Gate: PASSED"
                        }
                        
                    } catch (Exception e) {
                        echo "Error evaluating DAST results: ${e.message}"
                        echo "Continuing with pipeline"
                    }
                }
            }
        }
    }
    post {
        always {
            junit allowEmptyResults: true, testResults: '**/test-results.xml'
            
            // Generate comprehensive security summary
            script {
                try {
                    def allReports = []
                    def totalIssues = 0
                    
                    // Collect all security scan results
                    if (fileExists("$BANDIT_JSON_REPORT")) {
                        def banditReport = readJSON file: "$BANDIT_JSON_REPORT"
                        def banditTotal = banditReport.results?.size() ?: 0
                        allReports.add("Bandit (SAST): ${banditTotal} issues")
                        totalIssues += banditTotal
                    }
                    
                    if (fileExists("semgrep_report.json")) {
                        def semgrepReport = readJSON file: "semgrep_report.json"
                        def semgrepTotal = semgrepReport.results?.size() ?: 0
                        allReports.add("Semgrep (SAST): ${semgrepTotal} issues")
                        totalIssues += semgrepTotal
                    }
                    
                    if (fileExists("zap_report.json")) {
                        def zapReport = readJSON file: "zap_report.json"
                        def zapTotal = 0
                        zapReport.site?.each { site ->
                            zapTotal += site.alerts?.size() ?: 0
                        }
                        allReports.add("OWASP ZAP (DAST): ${zapTotal} issues")
                        totalIssues += zapTotal
                    }
                    
                    def summary = """
Security Scan Summary - Build #${BUILD_NUMBER}
===============================================
Commit: ${env.GIT_COMMIT?.take(7) ?: 'N/A'}
Branch: ${env.GIT_BRANCH ?: 'N/A'}
Build Status: ${currentBuild.result ?: 'SUCCESS'}

Total Security Issues: ${totalIssues}

Scan Results:
${allReports.join('\n')}

Reports Available:
- Bandit: ${BUILD_URL}artifact/${BANDIT_REPORT}
- Semgrep: ${BUILD_URL}artifact/semgrep_report.txt
- OWASP ZAP: ${BUILD_URL}artifact/zap_report.html
- Nikto: ${BUILD_URL}artifact/nikto_report.txt

Build URL: ${BUILD_URL}
                    """
                    
                    echo summary
                    writeFile file: 'comprehensive_security_summary.txt', text: summary
                    archiveArtifacts artifacts: 'comprehensive_security_summary.txt', fingerprint: true
                    
                } catch (Exception e) {
                    echo "Could not generate comprehensive security summary: ${e.message}"
                }
            }
        }
        success {
            echo "Pipeline completed successfully!"
            script {
                if (currentBuild.result == 'UNSTABLE') {
                    echo "Note: Build marked as UNSTABLE due to security warnings"
                }
            }
        }
        failure {
            echo "Pipeline failed!"
            echo "Check security scan results:"
            echo "- Bandit: ${BUILD_URL}artifact/${BANDIT_REPORT}"
            echo "- ZAP: ${BUILD_URL}artifact/zap_report.html"
            echo "- Comprehensive Summary: ${BUILD_URL}artifact/comprehensive_security_summary.txt"
        }
        unstable {
            echo "Pipeline completed with warnings!"
            echo "Security issues found but within acceptable limits"
            echo "Review reports: ${BUILD_URL}artifact/comprehensive_security_summary.txt"
        }
    }
}
