FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .

# VestBridge code is read-only inside container
RUN chmod -R 555 /app/src/

USER nobody
ENTRYPOINT ["vestbridge"]
CMD ["serve", "--broker", "paper"]
