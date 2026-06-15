# AI Chat Service — Docker 镜像
# 使用方式见 README.md 或 docker-compose.yml

FROM python:3.12-slim

WORKDIR /app

# 创建日志目录
RUN mkdir -p logs

# 安装依赖（先复制 requirements，利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目代码
COPY app/ ./app/
COPY knowledge/ ./knowledge/
COPY scripts/ ./scripts/
COPY pyproject.toml .

# 暴露服务端口
EXPOSE 8082

# 启动命令
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]
