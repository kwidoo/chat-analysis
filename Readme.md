# Chat Analysis System Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [API Reference](#api-reference)
7. [Development](#development)
8. [Contributing](#contributing)
9. [License](#license)

## Introduction

The Chat Analysis System is a comprehensive application designed for analyzing chat messages. It leverages advanced machine learning models for natural language processing, distributed computing for scalability, and containerization for easy deployment. The system provides features for uploading chat files, processing messages, searching for similar messages, and visualizing the results.

## System Architecture

The system is composed of the following main components:

- **Backend**: A Flask application that handles file uploads, processes messages, and provides API endpoints for searching and visualization.
- **Frontend**: A React application that provides a user interface for uploading files, searching messages, and viewing visualizations.
- **Dask**: A distributed computing library used for parallel processing of tasks.
- **FAISS**: A library for efficient similarity search and clustering of dense vectors.
- **Docker**: Containerization platform used for packaging and deploying the application.

## Installation

### Prerequisites

- **Python 3.8+**
- **Node.js 22+**
- **Docker**
- **Dask**

### Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd chat-analysis-system
   ```

2. **Build and run the Docker containers**:
   ```bash
   docker-compose up --build
   ```

3. **Access the application**:
   - Backend: `http://localhost:5000`
   - Frontend: `http://localhost:3000`

## Configuration

### Backend Configuration

The backend configuration is stored in `backend/config.py`. It includes settings for directories, model versions, and other parameters.

### Docker Configuration

The Docker configuration is defined in `docker-compose.yml`. It specifies the services, their dependencies, volumes, and networking.

## Usage

### Uploading Files

1. Open the frontend application at `http://localhost:3000`.
2. Click on the "Upload and Analyze" button.
3. Select the chat files you want to upload.

### Searching Messages

1. Enter a search query in the search bar.
2. Click the search button to retrieve similar messages.

### Visualizing Data

1. The dashboard provides interactive charts and visualizations of the processed data.

## API Reference

### Upload Endpoint

- **URL**: `/upload`
- **Method**: `POST`
- **Description**: Uploads chat files for processing.
- **Request Body**: Form data with files.
- **Response**: JSON with task ID and status.

### Search Endpoint

- **URL**: `/search`
- **Method**: `POST`
- **Description**: Searches for similar messages.
- **Request Body**: JSON with query and k-value.
- **Response**: JSON with search results.

### Visualization Endpoint

- **URL**: `/visualization`
- **Method**: `GET`
- **Description**: Retrieves data for visualization.
- **Response**: JSON with visualization data.

### Health Check Endpoint

- **URL**: `/health`
- **Method**: `GET`
- **Description**: Checks the health of the application.
- **Response**: JSON with health status.

## Development

### Setting Up the Development Environment

1. **Backend**:
   - Install Python dependencies:
     ```bash
     cd backend
     pip install -r requirements.txt
     ```

2. **Frontend**:
   - Install Node.js dependencies:
     ```bash
     cd frontend
     npm install
     ```

### Running the Application

1. **Backend**:
   ```bash
   cd backend
   python app.py
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm start
   ```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your changes to the branch.
5. Create a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Additional Notes

- The system uses FAISS for efficient similarity search and clustering.
- Dask is used for distributed computing to handle large-scale data processing.
- The frontend is built with React and provides an interactive user interface.
- Docker is used for containerization, making it easy to deploy and manage the application.

For any issues or questions, please open an issue in the repository.
