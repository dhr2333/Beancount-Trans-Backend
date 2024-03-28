pipeline {
    agent any
    environment {
        DOCKER_TAG = '20240330'
        DOCKER_IMAGE = 'registry.cn-hangzhou.aliyuncs.com/dhr2333/beancount-trans-backend'
        YAML = "image: ${DOCKER_IMAGE}:${DOCKER_TAG}"
    }
    stages {
        stage('Clone') {
            steps {
                git branch: 'main', credentialsId: '0bd011d1-722c-4a1a-a870-31eaff32761d', url: 'https://github.com/dhr2333/Beancount-Trans-Backend.git'
            }
        }
        stage('Build Image and Push') {
            steps {
                script {
                    docker.withRegistry('https://registry.cn-hangzhou.aliyuncs.com/dhr2333', '8972f1d0-8506-4197-9ffa-88f6f988650a') {
                        def customImage = docker.build("${DOCKER_IMAGE}:${DOCKER_TAG}", '-f Dockerfile-Backend .')
                        customImage.push()
                    }
                }
            }
        }
        stage('Start Service'){
            steps{
                sshPublisher(publishers: [sshPublisherDesc(configName: 'dhr2333', transfers: [sshTransfer(cleanRemote: false, excludes: '', execCommand: "echo ${DOCKER_TAG} \n echo \"${DOCKER_TAG}\" \n sed -i \"/registry.cn-hangzhou.aliyuncs.com\\/dhr2333\\/beancount-trans-backend/c\\\\    image: registry.cn-hangzhou.aliyuncs.com/dhr2333/beancount-trans-backend:${DOCKER_TAG}\" /root/Manage/docker-compose-beancount-trans.yaml \n docker compose -f /root/Manage/docker-compose-beancount-trans.yaml down \n docker compose -f /root/Manage/docker-compose-beancount-trans.yaml up -d", execTimeout: 120000, flatten: false, makeEmptyDirs: false, noDefaultExcludes: false, patternSeparator: '[, ]+', remoteDirectory: '', remoteDirectorySDF: false, removePrefix: '', sourceFiles: '')], usePromotionTimestamp: false, useWorkspaceInPromotion: false, verbose: false)])
            }
        }
    }
    post {  // 不管构建结果，都执行以下步骤
        success{  // 构建成功时
            echo 'success'

        }
        failure{
            echo 'failure'
        }
    }
}