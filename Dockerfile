FROM python:3.12

RUN mkdir /app
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt
COPY iss_tracker.py /app/iss_tracker.py
COPY test_iss_tracker.py /app/test_iss_tracker.py

RUN chmod 764 /app/iss_tracker.py

ENTRYPOINT ["python"]
CMD ["iss_tracker.py"]
