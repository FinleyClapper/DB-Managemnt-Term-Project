FROM python:3.11-slim
WORKDIR /app

#Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Set environment variables from .env
#KAGGLE_USERNAME=${lanayegbusi}
#KAGGLE_KEY=${0e9973f8822d3e55dad0727d011b3e30}
#Copy project files

COPY . .
ENV KAGGLE_CONFIG_DIR=/app/kaggle
CMD ["python", "main.py"]
