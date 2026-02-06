# End-to-End Realtime Streaming with Unstructured Data
![Python 3.12](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)
![Spark 4.1.1](https://img.shields.io/badge/Spark-4.1.1-orange?logo=apache-spark&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/Status-MVP-yellow)![License](https://img.shields.io/badge/License-MIT-green)

## 🚀 Quick Start
```bash
# Clone the repository
git clone https://github.com/adamxiang-end-to-end-realtime-streaming-with-unstructured-data.git
cd adamxiang-end-to-end-realtime-streaming-with-unstructured-data
# Start the Spark cluster with Docker
docker-compose up -d
# Submit the job
docker exec spark-master spark-submit /opt/bitnami/spark/jobs/main.py
# Monitor in Spark UI
open http://localhost:9090
```

