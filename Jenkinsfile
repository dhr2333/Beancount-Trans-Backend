pipeline {
    agent any

    stages {
        stage('Clone') {
            steps {
                git branch: 'main', url: 'git@github.com:dhr2333/Beancount-Trans-Backend.git'
            }
            // post {
            //     success {
            //         junit '**/target/surefire-reports/TEST-*.xml'  // 使用Junit自动化测试(先向开发了解项目中是否集成junit)
            //         archiveArtifacts 'target/*.jar'  // 归档
            //     }
            // }
        }
        stage('Build') {
            // steps {
            //     sh "mvn -B -pl wlh-electric -am clean package"  // 调用maven打包
            // }
        }
        stage('Deploy') {
            // steps {  // 192.168.254.23为kubernetes集群的master节点
            //     sshPublisher(publishers: [sshPublisherDesc(configName: '192.168.254.23', transfers: [sshTransfer(cleanRemote: false, excludes: '', execCommand: '''JAR_DIRECTORY=\'/usr/local/wlhiot/jenkins/svr/wlh-electric-0.0.1-SNAPSHOT.jar\'
            //     DOCKERFILE_DIRECTORY=\'/usr/local/wlhiot/container/docker/project/ebox/svr\'
            //     YAML_DIRECTORY=\'/usr/local/wlhiot/container/kubernetes/project/ebox/ebox.yaml\'
            //     IMAGE_NAME=\'192.168.254.29:8080/wlh_project/ebox_svr\'

            //     mv $JAR_DIRECTORY $DOCKERFILE_DIRECTORY  # 将编译好的jar包移动到包含Dokcerfile的目录
            //     cd $DOCKERFILE_DIRECTORY
            //     docker build -t $IMAGE_NAME .  # 打成docker镜像，镜像名称见变量
            //     docker login -u admin -p Harbor12345 192.168.254.29:8080  # 192.168.254.29:8080是harbor服务器，-u为用户-p为密码，登录harbor后才能推送
            //     docker push $IMAGE_NAME  # 推送
            //     docker rmi $IMAGE_NAME  # 删除现有镜像
            //     ansible k8s_node -m command -a "docker pull $IMAGE_NAME"  # 控制所有node节点拉取最新镜像(需提前配置好ansible)
            //     sed -i "/app.kubernetes.io\\/random/c\\ \\ \\ \\ \\ \\ \\ \\ app.kubernetes.io\\/random: \'$BUILD_ID\'"  $YAML_DIRECTORY  # 修改Yaml文件，每次构建便自动修改，apply更新服务时会重新拉取新镜像
            //     kubectl apply -f $YAML_DIRECTORY''',
            //     execTimeout: 120000, flatten: false, makeEmptyDirs: false, noDefaultExcludes: false, patternSeparator: '[, ]+', remoteDirectory: '/svr', remoteDirectorySDF: false, removePrefix: 'wlh-electric/target/', sourceFiles: 'wlh-electric/target/wlh-electric-0.0.1-SNAPSHOT.jar')], usePromotionTimestamp: false, useWorkspaceInPromotion: false, verbose: true)])
            // }  // 先用自由风格的方式写完正常跑后再一步一步调整为Pipeline方式，无数次的测试和调整，放宽心
        }        
        // stage('env') {
        //     steps {
        //         echo 'This is a sonar step' 
        //         def sonarqubeScannerHome = tool name: 'sonar-scanner'
        //         echo sonarqubeScannerHome
        //     }
        // }
        stage('sonarqube'){
            // steps {  // Jenkins下载sonarqube插件(包含sonarqube服务及sonar-scanner扫描器)后能通过sonar-scanner命令来自动监测
            //     // script {
            //     //     scannerHome = tool "sonar-scanner"
            //     //     echo "${scannerHome}"
            //     // }
            //     withSonarQubeEnv('sonarqube') {
            //         sh '/var/jenkins_home/tools/hudson.plugins.sonar.SonarRunnerInstallation/sonar-scanner/bin/sonar-scanner ' + // 我这边使用绝对路径，该命令在command中跑过
            //         '-Dsonar.host.url=http://192.168.254.23:30010/ ' +
            //         // '-Dsonar.login=daihaorui ' +
            //         // '-Dsonar.password=Mj!|"F/r&KGUWy^$t?^Y ' +
            //         '-Dsonar.projectname=ebox ' +
            //         '-Dsonar.projectKey=ebox ' +
            //         '-Dsonar.java.binaries=./wlh-electric/target/ ' +
            //         // '-Dsonar.projectBaseDir=/var/jenkins_home/workspace/i-Branch_Pipeline_ebox_daihaorui/ ' +
            //         '-Dsonar.sources=./wlh-electric/src/'
            //     }
            // }
        }
        stage('Web Test') {  // 自己编写的Web测试
            // steps {
            //     sh '''#!/bin/bash
            //     /bin/sleep 120
            //     cd /var/jenkins_home/mount/pytest/project/ebox/test/
            //     sudo python3 -m pytest --alluredir /var/jenkins_home/workspace/i-Branch_Pipeline_ebox_daihaorui/wlh-electric/target/allure-results --clean-alluredir
            //     sudo chown jenkins.jenkins /var/jenkins_home/workspace/i-Branch_Pipeline_ebox_daihaorui/wlh-electric/target/allure-results -R
            //     exit 0'''
            // }
        }
        stage('Allure Report') {  // 输出测试报告
            // steps {
            //     allure includeProperties: false, jdk: 'JDK8', report: 'allure-reports', results: [[path: 'wlh-electric/target/allure-results']]
            // }
        }
    }
    post {  // 不管构建结果，都执行以下步骤
        success{  // 构建成功时
            // dingtalk(  // 调用钉钉机器人输出
            //     robot: '86fa9893-5ae9-4e5e-b653-73fba6323e4e',
            //     type: 'MARKDOWN',
            //     title: "success: ${JOB_NAME}",
            //     text: ["- 成功构建: ${JOB_NAME}!"]
            //     )
        }
        failure{
            // emailext attachLog: true, body: '$DEFAULT_CONTENT', postsendScript: '$DEFAULT_POSTSEND_SCRIPT', presendScript: '$DEFAULT_PRESEND_SCRIPT', recipientProviders: [developers(), requestor()], replyTo: '$DEFAULT_REPLYTO', subject: '$DEFAULT_SUBJECT', to: 'daihaorui@wlhiot.com'  // 调用邮件输出
        }
    }
}