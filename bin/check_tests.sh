#!/bin/bash

# 测试状态检查脚本
# 用于快速验证项目测试的健康状态

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Beancount-Trans 测试状态检查${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${RED}❌ 未找到虚拟环境 .venv${NC}"
    echo -e "${YELLOW}请先创建虚拟环境：python -m venv .venv${NC}"
    exit 1
fi

# 激活虚拟环境
echo -e "${BLUE}🔧 激活虚拟环境...${NC}"
source .venv/bin/activate

# 检查pytest
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest未安装${NC}"
    echo -e "${YELLOW}安装测试依赖：pip install pytest pytest-django pytest-cov pytest-html${NC}"
    exit 1
fi

echo -e "${GREEN}✅ pytest已安装${NC}"
echo ""

# 收集测试
echo -e "${BLUE}📋 收集测试用例...${NC}"
TEST_COUNT=$(pytest --collect-only -q 2>&1 | grep "collected" | awk '{print $1}')
echo -e "${GREEN}✅ 收集到 ${TEST_COUNT} 个测试${NC}"
echo ""

# 运行测试
echo -e "${BLUE}🧪 运行测试...${NC}"
echo -e "${BLUE}========================================${NC}"

if pytest -v --tb=short; then
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
    
    # 显示覆盖率
    if [ -f "reports/coverage.xml" ]; then
        COVERAGE=$(grep -oP 'line-rate="\K[0-9.]+' reports/coverage.xml | head -1 | awk '{printf "%.1f", $1*100}')
        echo -e "${BLUE}📊 代码覆盖率: ${COVERAGE}%${NC}"
    fi
    
    # 显示报告位置
    echo ""
    echo -e "${BLUE}📝 测试报告：${NC}"
    echo -e "  - HTML报告: reports/pytest-report.html"
    echo -e "  - 覆盖率报告: reports/htmlcov/index.html"
    echo -e "  - JUnit XML: reports/junit.xml"
    
    exit 0
else
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${RED}❌ 部分测试失败${NC}"
    echo -e "${YELLOW}请查看上方详细错误信息${NC}"
    exit 1
fi




