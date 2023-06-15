pipeline {
    agent any

    stages {
        stage('Clone') {
            steps {
                git branch: 'develop', credentialsId: '0bd011d1-722c-4a1a-a870-31eaff32761d', url: 'https://github.com/dhr2333/Beancount-Trans-Backend.git'
            }
        }
        stage('Build Image and Push') {
            steps {
                script {
                    docker.withRegistry('http://harbor.dhr2333.cn:8080', 'a4a1bb2f-ee2a-4476-bc0f-f0b8df584cd1') {
                        def customImage = docker.build("harbor.dhr2333.cn:8080/library/beancount-trans:20230614")
                        customImage.push()
                    }
                }
            }
        }
        stage('Pull Image') {
            steps{
                echo 'Pull Image'
                sshPublisher(publishers: [sshPublisherDesc(configName: 'dhr2333', transfers: [sshTransfer(cleanRemote: false, excludes: '', execCommand: '''echo `hostname`
docker pull harbor.dhr2333.cn:8080/library/beancount-trans:20230614''', execTimeout: 1200000, flatten: false, makeEmptyDirs: false, noDefaultExcludes: false, patternSeparator: '[, ]+', remoteDirectory: '', remoteDirectorySDF: false, removePrefix: '', sourceFiles: '')], usePromotionTimestamp: false, useWorkspaceInPromotion: false, verbose: true)])
           }
        }
        stage('Start Service'){
            steps{
                echo 'Start Service'
            }
        }
    post {  // 不管构建结果，都执行以下步骤
        success{  // 构建成功时
            echo 'hello'

        }
        failure{
            echo 'hello'
        }
    }
}