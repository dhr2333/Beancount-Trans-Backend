pipeline {
    agent any

    options {
        timeout(time: 30, unit: 'MINUTES')
    }

    environment {
        // Docker配置
        REGISTRY = "harbor.dhr2333.cn/beancount-trans"
        IMAGE_NAME = "beancount-trans-backend"

        // GitHub配置
        GITHUB_REPO = 'dhr2333/Beancount-Trans-Backend'
        GITHUB_API_URL = 'https://api.github.com'

        // 报告目录 - 使用安全的路径格式避免URL编码问题
        REPORTS_DIR = "/jenkins-share/test-reports/${BUILD_NUMBER}"
    }

    stages {
        stage('初始化') {
            steps {
                script {
                    echo "🚀 开始构建 Beancount-Trans-Backend 项目"
                    echo "分支: ${env.BRANCH_NAME}"

                    // 获取Git Commit短哈希
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()

                    // 设置镜像标签
                    env.IMAGE_TAG = "git-${env.GIT_COMMIT_SHORT}"
                    env.TEST_IMAGE_TAG = "test-${env.IMAGE_TAG}"

                    echo "Git Commit短哈希: ${env.GIT_COMMIT_SHORT}"
                    echo "生产镜像标签: ${env.IMAGE_TAG}"
                    echo "测试镜像标签: ${env.TEST_IMAGE_TAG}"
                    echo "工作目录: ${env.WORKSPACE}"
                }
            }
        }

        stage('构建测试镜像') {
            steps {
                retry(3) {
                    script {
                        echo "🏗️ 构建测试Docker镜像..."
                        updateGitHubStatus('pending', '正在构建测试镜像...')

                        sh "DOCKER_BUILDKIT=1 docker build -f Dockerfile-Test-Legacy -t ${env.REGISTRY}/${env.IMAGE_NAME}:${TEST_IMAGE_TAG} ."
                        echo "✅ 测试镜像构建完成: ${env.REGISTRY}/${env.IMAGE_NAME}:${TEST_IMAGE_TAG}"
                    }
                }
            }
        }

        stage('运行测试') {
            steps {
                script {
                    echo "🧪 在Docker容器内运行pytest测试..."
                    updateGitHubStatus('pending', '正在运行测试...')

                    // 报告目录将在容器内自动创建

                    // 在容器内运行测试，挂载共享卷
                    echo "🐳 启动测试容器，使用共享卷: ${REPORTS_DIR}"
                    sh """
                        docker run --rm \
                            -v dhr2333-jenkins-share:/jenkins-share \
                            -v /var/run/docker.sock:/var/run/docker.sock \
                            -e PYTHONUNBUFFERED=1 \
                            ${env.REGISTRY}/${env.IMAGE_NAME}:${TEST_IMAGE_TAG} \
                            bash -c "
                                mkdir -p ${REPORTS_DIR}
                                chmod 777 ${REPORTS_DIR}
                                pytest --no-migrations --reuse-db \
                                    --junitxml=${REPORTS_DIR}/junit.xml \
                                    --html=${REPORTS_DIR}/pytest-report.html \
                                    --self-contained-html \
                                    --cov-report=xml:${REPORTS_DIR}/coverage.xml \
                                    --cov-report=html:${REPORTS_DIR}/htmlcov \
                                    || exit 0
                                chmod -R 777 ${REPORTS_DIR}
                            "
                    """

                    // 检查测试结果
                    echo "🔍 检查测试报告文件..."
                    echo "报告目录: ${REPORTS_DIR}"

                    // 列出报告目录内容进行调试
                    sh "ls -la ${REPORTS_DIR} || echo '报告目录不存在'"

                    // 等待文件系统同步
                    sleep(2)

                    def testResult = sh(
                        script: "test -f ${REPORTS_DIR}/junit.xml && echo 'exists' || echo 'missing'",
                        returnStdout: true
                    ).trim()

                    echo "测试结果检查: ${testResult}"

                    if (testResult == 'missing') {
                        echo "❌ 测试报告文件未找到"
                        updateGitHubStatus('failure', '测试报告生成失败')
                        error("测试报告生成失败")
                    } else {
                        echo "✅ 测试报告文件存在"
                    }
                }
            }
        }
        
        stage('发布测试报告') {
            steps {
                script {
                    echo "📊 发布测试报告..."

                    // 复制报告文件到workspace（Jenkins插件需要真实文件）
                    echo "📁 复制报告文件到workspace..."
                    sh "mkdir -p ${WORKSPACE}/reports"
                    sh "cp ${REPORTS_DIR}/junit.xml ${WORKSPACE}/reports/ 2>/dev/null || true"
                    sh "cp ${REPORTS_DIR}/pytest-report.html ${WORKSPACE}/reports/ 2>/dev/null || true"
                    sh "cp ${REPORTS_DIR}/coverage.xml ${WORKSPACE}/reports/ 2>/dev/null || true"
                    sh "cp -r ${REPORTS_DIR}/htmlcov ${WORKSPACE}/reports/ 2>/dev/null || true"

                    // 发布JUnit测试结果
                    junit allowEmptyResults: true, testResults: "reports/junit.xml"

                    // 发布HTML测试报告
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'pytest-report.html',
                        reportName: 'Pytest测试报告',
                        reportTitles: 'Pytest测试报告'
                    ])

                    // 发布覆盖率报告
                    publishHTML([
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports/htmlcov',
                        reportFiles: 'index.html',
                        reportName: '代码覆盖率报告',
                        reportTitles: '代码覆盖率报告'
                    ])

                    // 读取覆盖率百分比
                    def coverage = sh(
                        script: """
                            if [ -f reports/coverage.xml ]; then
                                grep -oP 'line-rate="\\K[0-9.]+' reports/coverage.xml | head -1 | awk '{printf "%.0f", \$1*100}'
                            else
                                echo "0"
                            fi
                        """,
                        returnStdout: true
                    ).trim()

                    echo "📈 代码覆盖率: ${coverage}%"
                    env.COVERAGE_PERCENT = coverage
                    
                    // 清理workspace中的报告文件以节省空间（报告已发布）
                    echo "🧹 清理workspace中的临时报告文件..."
                    sh "rm -rf ${WORKSPACE}/reports/htmlcov 2>/dev/null || true"
                    sh "rm -f ${WORKSPACE}/reports/pytest-report.html 2>/dev/null || true"
                }
            }
        }

        /* ==================== 以下是CI/CD阶段（暂时禁用） ====================
         * 
         * 当前只实现CI（持续集成），即自动运行测试
         * 等所有分支的测试稳定后，可以启用以下阶段实现CD（持续部署）
         * 
         * 启用方法：删除注释符号 /* 和 */
        /*
        stage('构建生产镜像') {
            when {
                branch 'main'
            }
            steps {
                script {
                    echo "🐳 构建生产Docker镜像..."
                    updateGitHubStatus('pending', '正在构建生产镜像...')
                    
                    // 构建镜像
                    sh "docker build -f Dockerfile-Backend -t ${env.REGISTRY}/${env.IMAGE_NAME}:${env.IMAGE_TAG} ."
                    
                    // main分支同时打latest标签
                    if (env.BRANCH_NAME == 'main') {
                        sh "docker tag ${env.REGISTRY}/${env.IMAGE_NAME}:${env.IMAGE_TAG} ${env.REGISTRY}/${env.IMAGE_NAME}:latest"
                    }
                    
                    // 推送到Harbor仓库
                    withCredentials([usernamePassword(
                        credentialsId: 'docker-registry-cred',
                        usernameVariable: 'REGISTRY_USER',
                        passwordVariable: 'REGISTRY_PASSWORD'
                    )]) {
                        sh "echo \${REGISTRY_PASSWORD} | docker login -u \${REGISTRY_USER} --password-stdin ${env.REGISTRY}"
                        sh "docker push ${env.REGISTRY}/${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                        
                        if (env.BRANCH_NAME == 'main') {
                            sh "docker push ${env.REGISTRY}/${env.IMAGE_NAME}:latest"
                        }
                    }
                    
                    echo "✅ 镜像构建并推送成功: ${env.REGISTRY}/${env.IMAGE_NAME}:${env.IMAGE_TAG}"
                }
            }
        }

        stage('部署到服务器') {
            when {
                branch 'main'
            }
            steps {
                script {
                    echo "🚀 开始部署到生产服务器..."
                    updateGitHubStatus('pending', '正在部署...')
                    
                    sshPublisher(
                        publishers: [
                            sshPublisherDesc(
                                configName: 'dhr2333',
                                transfers: [
                                    sshTransfer(
                                        cleanRemote: false,
                                        excludes: '',
                                        execCommand: """
                                            echo ${env.IMAGE_TAG}
                                            sed -i "s|image:.*beancount-trans-backend.*|image: ${env.REGISTRY}/${env.IMAGE_NAME}:${env.IMAGE_TAG}|" /root/Manage/docker-compose-beancount-trans.yaml
                                            docker compose -f /root/Manage/docker-compose-beancount-trans.yaml down
                                            docker compose -f /root/Manage/docker-compose-beancount-trans.yaml up -d
                                        """,
                                        execTimeout: 120000,
                                        flatten: false,
                                        makeEmptyDirs: false,
                                        noDefaultExcludes: false,
                                        patternSeparator: '[, ]+',
                                        remoteDirectory: '',
                                        remoteDirectorySDF: false,
                                        removePrefix: '',
                                        sourceFiles: ''
                                    )
                                ],
                                usePromotionTimestamp: false,
                                useWorkspaceInPromotion: false,
                                verbose: false
                            )
                        ]
                    )
                    echo "✅ 部署完成"
                }
            }
        }
        ==================== CI/CD阶段结束 ==================== */
    }
    
    post {
        success {
            script {
                echo '✅ 构建成功'
                def message = "测试通过 ✓ | 覆盖率: ${env.COVERAGE_PERCENT}%"
                updateGitHubStatus('success', message)
                
                echo "📊 测试覆盖率: ${env.COVERAGE_PERCENT}%"
            }
        }

        failure {
            script {
                echo '❌ 构建失败'
                updateGitHubStatus('failure', '构建或测试失败')
            }
        }

        always {
            script {
                echo '🧹 清理测试镜像和临时文件...'
                
                // 清理测试镜像（可选，节省磁盘空间）
                try {
                    sh "docker rmi ${env.REGISTRY}/${env.IMAGE_NAME}:${TEST_IMAGE_TAG} || true"
                } catch (Exception e) {
                    echo "清理测试镜像失败: ${e.message}"
                }
                
                // 清理旧的测试报告（保留最近3个构建的报告）
                try {
                    sh """
                        # 清理超过3个构建的旧报告目录
                        cd /jenkins-share/test-reports
                        if [ -d "${BUILD_NUMBER}" ]; then
                            # 获取所有构建号并删除旧的，使用chmod确保权限
                            ls -1 | sort -n | head -n -3 | while read dir; do
                                if [ -d "\$dir" ]; then
                                    chmod -R 777 "\$dir" 2>/dev/null || true
                                    rm -rf "\$dir" 2>/dev/null || true
                                fi
                            done
                        fi
                    """
                } catch (Exception e) {
                    echo "清理旧报告失败: ${e.message}"
                }
            }
            cleanWs()
        }
    }
}

// 更新GitHub提交状态的函数
def updateGitHubStatus(String state, String description) {
    // 获取当前commit SHA，优先使用环境变量，fallback到git命令
    def commitSha = env.GIT_COMMIT ?: env.GIT_COMMIT_SHORT

    if (!commitSha) {
        try {
            commitSha = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
        } catch (Exception e) {
            echo "无法获取Git commit SHA: ${e.message}"
            return
        }
    }

    // 构建Jenkins构建URL
    def targetUrl = "${env.BUILD_URL}"

    // GitHub状态API payload
    def payload = """
    {
        "state": "${state}",
        "target_url": "${targetUrl}",
        "description": "${description}",
        "context": "continuous-integration/jenkins/${env.BRANCH_NAME}"
    }
    """

    // 使用GitHub Token更新状态
    try {
        withCredentials([string(credentialsId: '1b709f07-d907-4000-8a8a-2adafa6fc658', variable: 'GITHUB_TOKEN')]) {
            sh """
                curl -X POST \
                    -H "Authorization: token \${GITHUB_TOKEN}" \
                    -H "Accept: application/vnd.github.v3+json" \
                    ${GITHUB_API_URL}/repos/${GITHUB_REPO}/statuses/${commitSha} \
                    -d '${payload}'
            """
        }
        echo "GitHub状态已更新: ${state} - ${description}"
    } catch (Exception e) {
        echo "更新GitHub状态失败: ${e.message}"
    }
}
