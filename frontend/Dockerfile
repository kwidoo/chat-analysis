FROM node:22-alpine

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY . .

# Build the app
RUN npm run build

# Start the app in development mode
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
