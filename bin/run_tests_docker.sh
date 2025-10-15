#!/bin/bash

# Docker容器内运行pytest测试脚本
# 用法: ./bin/run_tests_docker.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
TEST_IMAGE="beancount-trans-backend:test"
REPORTS_DIR="$(pwd)/reports"
DOCKERFILE="Dockerfile-Test"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Beancount-Trans 测试套件 (Docker)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ 错误: Docker未运行，请先启动Docker${NC}"
    exit 1
fi

# 清理旧报告
echo -e "${YELLOW}🧹 清理旧测试报告...${NC}"
sudo rm -rf "${REPORTS_DIR}"
mkdir -p "${REPORTS_DIR}"

# 构建测试镜像
echo -e "${BLUE}🏗️  构建测试Docker镜像...${NC}"
if docker build -f "${DOCKERFILE}" -t "${TEST_IMAGE}" .; then
    echo -e "${GREEN}✅ 测试镜像构建成功${NC}"
else
    echo -e "${RED}❌ 测试镜像构建失败${NC}"
    exit 1
fi

# 运行测试
echo ""
echo -e "${BLUE}🧪 在Docker容器内运行pytest测试...${NC}"
echo -e "${BLUE}========================================${NC}"

# 运行测试容器，挂载报告目录
if docker run --rm \
    -v "${REPORTS_DIR}:/app/reports" \
    "${TEST_IMAGE}" \
    pytest --no-migrations --reuse-db; then
    TEST_RESULT=0
else
    TEST_RESULT=$?
fi

echo ""
echo -e "${BLUE}========================================${NC}"

# 检查报告文件
if [ -f "${REPORTS_DIR}/junit.xml" ]; then
    echo -e "${GREEN}✅ JUnit报告已生成: ${REPORTS_DIR}/junit.xml${NC}"
else
    echo -e "${RED}⚠️  警告: JUnit报告未生成${NC}"
fi

if [ -f "${REPORTS_DIR}/pytest-report.html" ]; then
    echo -e "${GREEN}✅ HTML测试报告已生成: ${REPORTS_DIR}/pytest-report.html${NC}"
else
    echo -e "${RED}⚠️  警告: HTML测试报告未生成${NC}"
fi

if [ -f "${REPORTS_DIR}/coverage.xml" ]; then
    echo -e "${GREEN}✅ 覆盖率XML已生成: ${REPORTS_DIR}/coverage.xml${NC}"
else
    echo -e "${RED}⚠️  警告: 覆盖率XML未生成${NC}"
fi

if [ -d "${REPORTS_DIR}/htmlcov" ]; then
    echo -e "${GREEN}✅ 覆盖率HTML报告已生成: ${REPORTS_DIR}/htmlcov/index.html${NC}"
else
    echo -e "${RED}⚠️  警告: 覆盖率HTML报告未生成${NC}"
fi

# 读取并显示覆盖率
if [ -f "${REPORTS_DIR}/coverage.xml" ]; then
    COVERAGE=$(grep -oP 'line-rate="\K[0-9.]+' "${REPORTS_DIR}/coverage.xml" | head -1 | awk '{printf "%.1f", $1*100}')
    echo ""
    echo -e "${BLUE}📊 代码覆盖率: ${COVERAGE}%${NC}"
fi

# 清理测试镜像（可选）
echo ""
read -p "是否删除测试镜像? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}🗑️  删除测试镜像...${NC}"
    docker rmi "${TEST_IMAGE}" || true
    echo -e "${GREEN}✅ 测试镜像已删除${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"

# 返回测试结果
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ 测试全部通过!${NC}"
    exit 0
else
    echo -e "${RED}❌ 部分测试失败，请查看报告${NC}"
    exit 1
fi


