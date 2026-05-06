# Project Spec

## Overview

Develop a cloud-based web application leveraging AWS S3, API Gateway, Lambda, DynamoDB, and compute services such as EC2 or ECS.

## Project Statement

Create a simple online music subscription web application using AWS services.

### Database (DynamoDB) and Storage (S3) Initialization

Q1. Write a program to create a login table in DynamoDB containing 10 entities with the following attributes: `email`, `user_name` and `password`, with their values following the the given schema:

| email (Type: String)            | user_name (Type: String) | password (Type: String) |
| ------------------------------- | ------------------------ | ----------------------- |
| `s#######0@student.rmit.edu.au` | `FirstnameLastname0`     | `012345`                |
| `s#######1@student.rmit.edu.au` | `FirstnameLastname1`     | `123456`                |
| `…`                             | `…`                      | `…`                     |
| `s#######9@student.rmit.edu.au` | `FirstnameLastname9`     | `901234`                |

For this specific cloud infrastructure assignment, storing passwords in plain text (as supplied in the dataset) is permitted for simplicity.

Q2. Write a program to create a table titled music in DynamoDB with the following attributes: `title`, `artist`, `year`, `album`, and `image_url`.

Q3. Write a program to load the data from [2026a2_songs.json](https://rmit.instructure.com/courses/158468/files/51277038?wrap=1 "2026a2_songs.json") to your music table. Before creating your table, you must analyse the raw data within the `2026a2_songs.json` dataset to understand the specific cardinality and relationships between song titles, artists, and albums. You must meticulously design your DynamoDB key schema based on these insights. The data populated into your music table must be a perfectly aligned, lossless representation of the raw JSON data, ensuring no songs are accidentally overwritten during the import.

Q4. Write a program that automatically downloads all artist images based on the `image_url` values found in 2026a2_songs.json and then uploads these images to an S3 bucket.

### **Web Application Functional Requirements**

#### Login Page

The login page contains an **Email** text field, a **Password** field, and a **Login** button as well as a **register** link.

- When user clicks the **Login** button, it will validate if the user-entered credentials match with the information stored in the **login** table.
- If the user credential is invalid, the login page will display "**email or password is invalid**"; it will be redirected to the **main** page otherwise.

#### Register Page

The **register** page contains an **Email** text field, a **Username** field, a **Password** field, and a **Register** button.

- When a user clicks the **Register** button, it will validate if the user-entered email matches with the email stored in the **login** table. (Note: Each registration must have a unique email address. The username is not intended to serve as a unique credential for authentication).
- If the entered email matches with the email stored in the **login** table, the register page will show "**The email already exists**".
- If the entered email is unique, the new user information will be stored in the **login** table, and the user will be redirected to the **login** page.

#### Main Page

The main page contains three areas (a **user area**, a **subscription area**, and a **query area**) and a **Logout** link. Displaying all songs stored in the database is not advisable, since in a real-world scenario it could contain millions of songs. For newly registered users, the subscription area must initially be empty and displayed in a clean state.

- After a user log in, the **user area** will show the corresponding **user_name**.
- **The subscription area w**ill show all the user subscribed music information stored in DynamoDB.
  - Each music information is followed by **the corresponding artist image retrieved from S3** and a "**Remove**" button.
  - If the user clicks "**Remove**", the corresponding information will be removed from the subscription area and the DynamoDB table.
- **The query area** should contain text areas for "**Title**", "**Year**", "**Artist**", "**Album**", and a "**Query**" button. At least one field must be completed.
  - If not contained in the table, show "**No result is retrieved. Please query again**".
  - If contained, show all retrieved music information. (Multiple conditions are connected by "AND" by default). Each is followed by the artist image from S3 and a "**Subscribe**" button. Clicking "**Subscribe**" adds it to the subscription area and stores it in DynamoDB.
    Note: During the demonstration, markers will provide specific search criteria, e.g., "Please find all songs by Taylor Swift in the album Fearless", “Please find all songs of Jimmy Buffett in 1974".
- When the user clicks **"Logout"**, they must be redirected to the login page. The user session should be terminated upon logout.

The web application must be highly functional, logically laid out, and user-friendly. It must successfully incorporate all required UI elements and error messages specified in the tasks.

### Web Application Frontend Design

You are responsible for designing and implementing the frontend of the application.

If the frontend primarily consists of static assets, you should carefully evaluate your hosting approach, considering factors such as scalability, operational simplicity, and cost-efficiency, rather than defaulting to a general-purpose compute service.

### Web Application Backend Design

The backend of the web application must be implemented separately using all three architectural approaches described below. Each backend implementation must be fully functional and capable of performing CRUD operations on both the DynamoDB **music** table and the **login** table.

1. **Amazon EC2** - A virtual server–based backend service.
2. **Amazon ECS** - A containerised backend deployment.
3. **API Gateway + AWS Lambda** - A fully serverless backend implementation.

Note: Each architecture must be deployed and validated **independently** to demonstrate functional equivalence.

### Final Important Development Notes

1. When you use or adapt code developed by someone else, include an inline comment in the code citing your source where possible
2. The whole application must be **fully deployed in AWS** on all 3 backends independently. This requirement ensures that students demonstrate practical competency in deploying, configuring, and integrating cloud-native services within a real cloud environment. The purpose of this assignment is not only to develop application functionality, but also to validate your ability to design and operate cloud infrastructure using AWS services. As this is a cloud infrastructure project, full AWS deployment is essential to meet the learning objectives and assessment criteria.
3. **Using Elastic Beanstalk is NOT allowed as a valid means of deploying your application.**
4. Ensure your web application runs on the standard HTTP(S) ports: 80 or 443.
5. AWS supports multiple programming languages; you can use any language(s) that you are familiar with. Your application still needs to fulfil the same requirements. You can use any framework providing you are writing the code for the core functions.
6. AWS Academy account does not allow to create any IAM roles. However, a role named `LabRole` has been pre-created for you. Use `LabRole` instead.
7. Students would also need to securely access the objects stored in S3. This is considered security best practice and should always be done.
8. Students must carefully design the DynamoDB key schema and indexing strategy, **including at least one Global Secondary Index (GSI) and one Local Secondary Index (LSI)**, to support efficient query patterns. Indexes should be purposefully designed rather than added arbitrarily.
9. **Both the Query and Scan operations** should be implemented appropriately for data retrieval from DynamoDB tables.
10. Please ensure that your implementation correctly handles different HTTP request methods (including **GET, POST, and DELETE**) when using the API Gateway REST API, and that each method is properly mapped to its corresponding database operation. Students are expected to implement a genuinely **RESTful API**, rather than routing all actions through a generic POST request.
