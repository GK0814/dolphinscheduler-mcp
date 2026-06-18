FROM python:3.9-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Expose MCP server port
EXPOSE 8089

# Run server with Streamable HTTP transport
CMD ["ds-mcp", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8089", "--path", "/mcp"]
