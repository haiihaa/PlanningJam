# Acknowledgements
This application was initially created as a final project for the MET CS 673 (Software Engineering) course at Boston University, taught by Professor Yuting Zhang.

[Original Project Github Link](https://github.com/BUMETCS673/cs673olf25project-cs673olf25_team3)

It is currently being adapted and extended as part of the MET CS 783 (Secure Software System) course. The primary objective is to use the existing codebase as a foundation for identifying security vulnerabilities and implementing robust security enhancements.

This work is purely for academic purposes and is not intended for commercial or for-profit use.

# Overview

PlanningJam is a social app designed to make organizing hangouts simple and fun. Users can log in, post plans, and invite friends to join. Friends can respond **Yes** to show their interest, while users can filter plans by type and send friend requests to connect more easily. The app helps people discover activities and coordinate plans efficiently.

---

## Table of Contents

- [Team Members and Roles](#-team-members-and-roles)
- [Features](#-features)
- [Project Setup and Run Guide](#project-setup-and-run-guide)
  - [System Requirements](#system-requirements)
  - [Frontend Development](#frontend-development)
  - [Backend Development](#backend-development)
  - [Database](#database)
  - [Docker](#docker)
  - [Testing](#running-tests)
- [Essential Roadmap](#essential-roadmap)
- [Desirable Roadmap](#desirable-roadmap)
- [Optional Roadmap](#optional-roadmap)
- [Tech Stack](#️-tech-stack)

---

## 🧑‍💻 Team Members and Roles
- **David** – Team Leader  
- **Ashley** – Requirement Leader  
- **Haolin** – Design and Implementation Leader  
- **Jason** – QA Leader
- **Donjay** – Configuration Leader

---

## ✨ Features
- User login and authentication  
- Post and share plans  
- Friends RSVP with Yes responses  
- Filter plans by type (e.g., food, sports, study, concerts)  
- Send and accept friend requests  

---

## Project Setup and Run Guide

### System Requirements

This project requires the following to run properly:

- **Node:** version 20.19 or higher
- **Python:** version 3.10 or higher

### Frontend Development 

The frontend is built using the React framework with Vite build tool.

#### Setting Up The Frontend

All frontend development should be done in the `frontend/` directory.

Install dependencies within the `frontend` directory
```
cd frontend
npm install
```


In the `frontend` directory, copy the contents in the `.env.example` file into a new `.env` file. 
Set the VITE_BASE_URL to be the api base url, which will likely be http://localhost:8000/. If not, check where the backend points to later.

    ```
    VITE_API_BASE_URL=http://localhost:8000
    ```


#### Running the Frontend

To run the frontend locally, run the following command:
```
npm run dev
```

### Backend Development 

The backend is built using the Django framework. 

**Backend structure:**
```
├── app/                # the core django framework
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── api/                # the api application
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── manage.py
└── requriements.txt    # dependency packages
└── .venv/
```

#### Setting Up The Backend 
All backend development should be done in the `backend/` directory. To setup the backend:

1. Create a python virtual environment in the backend directory

    ```
    cd backend
    python -m venv .venv
    ```

2. Activate the `venv`

    ```
    # for macOS or Linux
    source .venv/bin/activate

    # for Windows
    .venv\Scripts\activate
    ```

3. Install the dependencies

    ```
    pip install -r requirements.txt
    ```

    *Note:* 

    When installing new packages, update the `requirements.txt` with the following:

    ```
    pip freeze > requirements.txt
    ```

4. Setup the environment variables

    In the `backend` directory, copy the contents in the `.env.example` file into a new `.env` file. 

    Then generate a new Django `SECRET KEY` with the following commands:
    ```
    python manage.py shell
    from django.core.management.utils import get_random_secret_key
    get_random_secret_key()
    ```

    Copy the generated key into the `.env` file.

    ```
    ...
    SECRET_KEY=your_django_secret_key_here

    ...
    ```

#### Setting Up MongoDB With The Backend

1. Configure the MongoDB Connection

    In the `backend/.env` file, add the MongoDB host url and credentials.

    i.e. 
    ```
    MONGO_HOST=mongodb://localhost
    MONGO_DATABASE_NAME=database_name
    MONGO_DATABASE_USER=database_user
    MONGO_DATABASE_PWD=database_password
    MONGO_DATABASE_PORT=27017
    MONGO_DATABASE_TLS=true #set false if using a local mongodb
    MONGO_DATABASE_SSL=true #set false if using a local mongodb
    ```

    *Note:* If both the backend and the MongoDB are both running on docker containers, the host url for the database will not be accessible via `localhost`. Connect the MongoDB container to the docker network `planjam-network` if its not already connected, then use the container name in place of `localhost`, i.e. `mongodb://mongodb`

    ```
    docker network connect planjam-network <mongodb_container_name>
    ```

2. Verify the connection is working by running the server. 

    ```
    python manage.py migrate
    ```

#### Running the Backend

To run the backend locally, run the following command:

```
python manage.py runserver
```

The django application should be accessible through the endpoint `http://localhost:8000`.

### Database

#### Installing a local MongoDB with Docker

The `database/` directory contains a docker-compose file to build a MongoDB docker container. 

To install a MongoDB database:
1. Before running the docker file, create a `.env` file in the `database/` directory and copy the contents from the `.env.example`. 

    Enter a root user and a root password for the MongoDB application. Modify the port if the port is already in use.
    ```
    MONGO_ROOT_USER=enter_a_root_user
    MONGO_ROOT_PASSWORD=enter_a_root_password
    MONGO_PORT=27017
    ```

2. Run the following to create a Docker network if not already created:
    ```
    docker network create planjam-network
    ```
    This will create the network `planjam-network`, allowing other containers in the same network to communicate with each other. 


3. Run the `docker-compose` command in this directory to build the container:
    ```script
    cd database
    docker-compose -p planningjam_database up -d
    ```
    This will create a Docker container called `planningjam_database` and build a mongodb service. 


#### Creating the Database

Connect to the mongodb with the root credentials and port set in the `.env` file.
```
mongosh "mongodb://<root_username>:<root_password>@localhost:<port>/planningjam?authSource=admin"
```

Within the mongosh shell, setup a new database called `planningjam`
```
use planningjam
```

Create a new user with read and write permission to the database. Set the username and password for the database user credentials. 
```
db.createUser({
  user: "<username>",
  pwd: "<password>",
  roles: [{ role: "readWrite", db: "planningjam" }]
})
```

Exit the mongo shell and test the new user by logging in to the MongoDB with the new user credentials and port.
```
mongosh "mongodb://<db_user>:<db_password>@localhost:<port>/planningjam
```

### Docker

The frontend and backend for this project can be run using dockerized containers. Before beginning, ensure the following are installed:

- **Docker** - [https://www.docker.com/](https://www.docker.com/)
- **Docker Compose**

#### Getting Started

1. Run the following to create a Docker network if not already created:
    ```
    docker network create planjam-network
    ```
    This will create the network `planjam-network`, allowing other containers in the same network to communicate with each other. 

2. From the project's root directory run the following command
    ```
    docker-compose -p planningjam up --build
    ```
    This command creates a new docker project called `planningjam` and creates container images for the frontend (django) and backend (react) application's services.

    To run the container in the background, use the -d (detached) flag:
    ```
    docker-compose -p planningjam up --build -d
    ```

    After the services are up and running, you can access the applications at the following URLs:

    - Backend (Django): http://localhost:8000

    - Frontend (Vite/React): http://localhost:5173

#### Docker Network IP

There may be instances where a container needs to communicate with another container through their network `IP Address` instead of `localhost`, i.e. the backend container needs to communicate with the mongodb container. 

To obtain the a list of IP Addresses in a network, execute the command 
```
docker network inspect <network_name_or_id>
```

*Note:* The Docker network for the project is called `planjam-network`.

#### Running Docker Containers Separately

While `docker-compose` is designed for managing multiple services at once, `docker run` is used to create and start a single container. 

Either the frontend or backend can be run independently using the `docker run` command to build and run the container from the `Dockerfile` configured in their respective directory. 

**Running the Frontend**

To run the frontend, first build the container with the following
```
docker build -t planningjam-frontend ./frontend
```

and then run it with
```
docker run -d --name planningjam-frontend -p 5173:5173 planningjam-frontend
```
The application should then be accessible at http://localhost:5173 .

**Running the Backend**

To run the backend, first build the container with the following
```
docker build -t planningjam-backend ./backend
```

and then run it with
```
docker run -d --name planningjam-backend -p 5173:5173 planningjam-backend
```

The application should then be accessible at http://localhost:8000 .

### Running Tests

#### Running backend tests

The backend tests files are located in the `/backend/api/tests` directory. A test file must have the following naming structure:
```
tests.py, test_*.py, *_tests.py, or *_test.py
```

To run tests on the backend locally, the working directory must be in the backend directory. 

```
# to run all tests
pytest -v

# to run a specific test file
pytest api/tests/<test_file>.py -v
```

To run the test within docker, 

```
docker build -t planningjam-api-test --target test .
docker run --rm planningjam-api-test
```

 
---

**Running frontend tests**
To run tests on the frontend you can do it locally or through docker. You must cd into the frontend folder first
Locally:
```
npm test
```
Docker: 
```
docker build -t planningjam-test --target test .
docker run planningjam-test
```

## Essential Roadmap
- Application (front end and backend) up
- User Authentication
- Friend Requests
- Have people be able to create plans
- Filter plans by type
- Invitees can RSVP

## Desirable Roadmap
- User Profile Management
- Plan Editing and Deletion
- Notifications for new plans
- Dismissing Plans
- Notifications for RSVPs

## Optional Roadmap
- Calendar Integration for own plans
- Plan Suggestions Based on Interests
- Calendar Integration for RSVP’d plans



---

## 🛠️ Tech Stack
- **Frontend:** React  
- **Backend:** Django / Python  
- **Database:** Django ORM (or any configured database)  
- **Authentication:** Django Auth / JWT  

---

