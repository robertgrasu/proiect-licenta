FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download ro_core_news_sm

COPY . .

RUN mkdir -p static/uploads

EXPOSE 5001

CMD ["python", "proiect_licenta.py"]
