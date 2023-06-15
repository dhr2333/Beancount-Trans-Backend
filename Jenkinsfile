pipeline {
    agent any

    stages {
        stage('Clone') {
            steps {
                git branch: 'develop', credentialsId: '0bd011d1-722c-4a1a-a870-31eaff32761d', url: 'https://github.com/dhr2333/Beancount-Trans-Backend.git'
            }
        }
       stage('Test') {
            steps{
                echo 'hello'
            }        
       }
        stage('Build Docker Image') {
            steps {
                script {
                    def customImage = docker.build("harbor.dhr2333.cn:8080/library/beancount-trans:20230614")
                }
            }
        }
        stage('Push Docker Image') {
            steps{
                script {
                    docker.withRegistry('http://harbor.dhr2333.cn:8080', credentialsId: 'a4a1bb2f-ee2a-4476-bc0f-f0b8df584cd1') {
                        customImage.push()
                    }
                }
            }
        }
        stage('env') {
            steps{
                echo 'hello'
            }
        }
        stage('sonarqube'){
            steps{
                echo 'hello'
            }
        }
        stage('Web Test') {
            steps{
                echo 'hello'
            }
        }
        stage('Allure Report') {
            steps{
                echo 'hello'
            }
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