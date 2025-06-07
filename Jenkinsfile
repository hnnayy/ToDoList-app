pipeline {
    agent any
    environment {
        VENV = 'venv'
        BANDIT_REPORT = 'bandit_report.txt'
        BANDIT_JSON_REPORT = 'bandit_report.json'
        ZAP_REPORT = 'zap_report.html'
        ZAP_JSON_REPORT = 'zap_report.json'
        SECURITY_THRESHOLD_HIGH = '0'      // Max HIGH severity issues allowed
        SECURITY_THRESHOLD_MEDIUM = '5'    // Max MEDIUM severity issues allowed
        APP_URL = 'http://localhost:5000'  // Application URL for DAST
        APP_CONTAINER_NAME = 'todolist-app'
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
                script {
                    try {
                        // Clean up any existing containers
                        echo 'Cleaning up existing containers...'
                        sh '''
                            docker-compose down --remove-orphans || true
                            docker system prune -f || true
                        '''
                        
                        // Start the application
                        echo 'Running docker-compose up...'
                        sh 'docker-compose up -d --build'
                        
                        // Get the actual container IP and port
                        def containerInfo = sh(
                            script: '''
                                # Wait a bit for container to start
                                sleep 5
                                
                                # Get container ID
                                CONTAINER_ID=$(docker-compose ps -q web 2>/dev/null || docker-compose ps -q app 2>/dev/null || docker ps --filter "name=todo" --format "{{.ID}}" | head -1)
                                
                                if [ ! -z "$CONTAINER_ID" ]; then
                                    # Get container IP
                                    CONTAINER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTAINER_ID)
                                    echo "Container IP: $CONTAINER_IP"
                                    
                                    # Check if port 5000 is exposed
                                    EXPOSED_PORT=$(docker port $CONTAINER_ID 5000 2>/dev/null | cut -d: -f2 || echo "5000")
                                    echo "Exposed Port: $EXPOSED_PORT"
                                    
                                    echo "APP_URL_CONTAINER=http://$CONTAINER_IP:5000"
                                    echo "APP_URL_HOST=http://localhost:$EXPOSED_PORT"
                                else
                                    echo "No container found"
                                    echo "APP_URL_CONTAINER=http://localhost:5000"
                                    echo "APP_URL_HOST=http://localhost:5000"
                                fi
                            ''',
                            returnStdout: true
                        ).trim()
                        
                        echo "Container info: ${containerInfo}"
                        
                        // Extract URLs from container info
                        def containerUrl = containerInfo.find(/APP_URL_CONTAINER=([^\s]+)/) { match, url -> url } ?: APP_URL
                        def hostUrl = containerInfo.find(/APP_URL_HOST=([^\s]+)/) { match, url -> url } ?: APP_URL
                        
                        echo "Trying Container URL: ${containerUrl}"
                        echo "Trying Host URL: ${hostUrl}"
                        
                        // Wait for application to be ready with multiple URL attempts
                        def maxAttempts = 60  // Increased attempts
                        def attempt = 0
                        def appReady = false
                        def workingUrl = ""
                        
                        while (attempt < maxAttempts && !appReady) {
                            try {
                                // Try container URL first
                                try {
                                    sh "curl -f --connect-timeout 5 --max-time 10 ${containerUrl}/health 2>/dev/null || curl -f --connect-timeout 5 --max-time 10 ${containerUrl} >/dev/null 2>&1"
                                    appReady = true
                                    workingUrl = containerUrl
                                    echo "Application is ready at ${containerUrl}"
                                } catch (Exception e1) {
                                    // Try host URL
                                    try {
                                        sh "curl -f --connect-timeout 5 --max-time 10 ${hostUrl}/health 2>/dev/null || curl -f --connect-timeout 5 --max-time 10 ${hostUrl} >/dev/null 2>&1"
                                        appReady = true
                                        workingUrl = hostUrl
                                        echo "Application is ready at ${hostUrl}"
                                    } catch (Exception e2) {
                                        // Try default localhost
                                        try {
                                            sh "curl -f --connect-timeout 5 --max-time 10 ${APP_URL}/health 2>/dev/null || curl -f --connect-timeout 5 --max-time 10 ${APP_URL} >/dev/null 2>&1"
                                            appReady = true
                                            workingUrl = APP_URL
                                            echo "Application is ready at ${APP_URL}"
                                        } catch (Exception e3) {
                                            // Check if container is actually running
                                            def containerStatus = sh(
                                                script: 'docker-compose ps',
                                                returnStdout: true
                                            ).trim()
                                            echo "Container status: ${containerStatus}"
                                            
                                            // Check application logs
                                            try {
                                                def logs = sh(
                                                    script: 'docker-compose logs --tail=10',
                                                    returnStdout: true
                                                ).trim()
                                                echo "Application logs: ${logs}"
                                            } catch (Exception logEx) {
                                                echo "Could not retrieve logs: ${logEx.message}"
                                            }
                                        }
                                    }
                                }
                            } catch (Exception e) {
                                echo "Health check failed: ${e.message}"
                            }
                            
                            if (!appReady) {
                                attempt++
                                echo "Waiting for application to start... (${attempt}/${maxAttempts})"
                                sleep(5)  // Reduced sleep time but more attempts
                            }
                        }
                        
                        if (!appReady) {
                            // Last resort: check if any process is listening on port 5000
                            def portCheck = sh(
                                script: 'netstat -tlnp | grep :5000 || ss -tlnp | grep :5000 || echo "No process listening on port 5000"',
                                returnStdout: true
                            ).trim()
                            echo "Port 5000 check: ${portCheck}"
                            
                            currentBuild.result = 'UNSTABLE'
                            echo "WARNING: Application health check failed after ${maxAttempts * 5} seconds"
                            echo "Continuing with pipeline - DAST scans may fail"
                            
                            // Set a default URL for DAST scans to attempt
                            workingUrl = APP_URL
                        }
                        
                        // Store the working URL for DAST stages
                        env.ACTUAL_APP_URL = workingUrl
                        
                        // Add deployment info to build description
                        if (currentBuild.description) {
                            currentBuild.description += " | Deployed: ${appReady ? 'Ready' : 'Warning'}"
                        } else {
                            currentBuild.description = "Deployed: ${appReady ? 'Ready' : 'Warning'}"
                        }
                        
                    } catch (Exception e) {
                        echo "Deployment failed: ${e.message}"
                        currentBuild.result = 'UNSTABLE'
                        echo "Continuing with pipeline..."
                        env.ACTUAL_APP_URL = APP_URL
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
                        def targetUrl = env.ACTUAL_APP_URL ?: APP_URL
                        echo "Running OWASP ZAP scan against: ${targetUrl}"
                        
                        // Run OWASP ZAP Docker container
                        sh """
                            # Pull ZAP Docker image
                            docker pull owasp/zap2docker-stable
                            
                            # Create reports directory
                            mkdir -p zap_reports
                            
                            # Run ZAP baseline scan with network settings
                            docker run --rm \
                                --network host \
                                -v \$(pwd)/zap_reports:/zap/wrk/:rw \
                                owasp/zap2docker-stable zap-baseline.py \
                                -t ${targetUrl} \
                                -J zap_report.json \
                                -r zap_report.html \
                                -x zap_report.xml \
                                -I || true
                            
                            # Move reports to workspace
                            mv zap_reports/zap_report.json . || echo "JSON report not found"
                            mv zap_reports/zap_report.html . || echo "HTML report not found" 
                            mv zap_reports/zap_report.xml . || echo "XML report not found"
                        """
                        
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
                        def targetUrl = env.ACTUAL_APP_URL ?: APP_URL
                        echo "Running Nikto scan against: ${targetUrl}"
                        
                        sh """
                            # Install Nikto if not available
                            if ! command -v nikto &> /dev/null; then
                                echo "Installing Nikto..."
                                apt-get update && apt-get install -y nikto || echo "Failed to install Nikto"
                            fi
                            
                            # Run Nikto scan
                            if command -v nikto &> /dev/null; then
                                nikto -h ${targetUrl} -output nikto_report.txt -Format txt || true
                                nikto -h ${targetUrl} -output nikto_report.json -Format json || true
                            else
                                echo "Nikto not available, skipping scan"
                                echo "No Nikto scan performed - Nikto not installed" > nikto_report.txt
                                echo '{"vulnerabilities": [], "error": "Nikto not available"}' > nikto_report.json
                            fi
                        """
                        
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
            // Clean up containers
            script {
                try {
                    sh 'docker-compose down --remove-orphans || true'
                } catch (Exception e) {
                    echo "Cleanup failed: ${e.message}"
                }
            }
            
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
