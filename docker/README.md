# MedKnowBridge Docker Environment

This directory contains Docker configuration files to run the MedKnowBridge system with all its dependencies in a containerized environment.

## Components

The Docker Compose setup includes the following services:

1. **MedKnowBridge API** - The main application providing the REST API for medical knowledge management and prompt handling
2. **BlazegraphDB** - A high-performance graph database for storing semantic medical knowledge

## Prerequisites

- Docker and Docker Compose installed on your system
- At least 2GB of RAM available for the containers

## Getting Started

### Starting the Services

To start all services, run:

```bash
./start_services.sh
```

This script will:
1. Build and start all containers
2. Wait for services to be healthy
3. Initialize the required namespaces in BlazegraphDB
4. Display URLs to access the services

### Stopping the Services

To stop all services, run:

```bash
./stop_services.sh
```

## Accessing the Services

Once the services are running, you can access:

- **MedKnowBridge API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **BlazegraphDB**: http://localhost:9999/blazegraph

## Data Persistence

Data is persisted using Docker volumes:

- `medknowbridge_blazegraph_data`: Stores the BlazegraphDB data

## Configuration

### Customizing the Environment

You can customize the environment by modifying the following files:

- `docker-compose.yml`: Service configuration
- `Dockerfile`: MedKnowBridge application container
- `init_namespaces.py`: BlazegraphDB namespace initialization

### Environment Variables

The following environment variables can be modified in the `docker-compose.yml` file:

- `BLAZEGRAPH_URL`: URL of the BlazegraphDB service (default: http://blazegraph:8080/blazegraph)
- `PORT`: Port for the MedKnowBridge API (default: 8000)

## Troubleshooting

### Viewing Logs

To view logs for all services:

```bash
docker-compose logs
```

To view logs for a specific service:

```bash
docker-compose logs medknowbridge  # For the API service
docker-compose logs blazegraph     # For the BlazegraphDB service
```

### Common Issues

1. **Services not starting**: Check if the required ports (8000, 9999) are already in use
2. **BlazegraphDB not initializing**: Check the logs for any error messages
3. **API not connecting to BlazegraphDB**: Ensure the BlazegraphDB service is healthy

## Development

### Making Changes to the API

If you make changes to the MedKnowBridge code, you'll need to rebuild the Docker image:

```bash
docker-compose build medknowbridge
docker-compose up -d medknowbridge
```

### Adding New Templates

Templates are mounted as a volume, so you can add new templates to the `prompt/templates` directory without rebuilding the image.
