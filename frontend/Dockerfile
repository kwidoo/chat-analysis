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

# Install serve to run the application
RUN npm install -g serve

# Start the app
CMD ["serve", "-s", "build", "-l", "3000"]
