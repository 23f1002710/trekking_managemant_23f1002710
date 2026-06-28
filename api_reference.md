# TMA (Trekking Management Application) API Reference

This document outlines the planned JSON-based RESTful API endpoints for the optional enhancements of the application. These endpoints can be used to interact with the system programmatically using standard HTTP methods.

## Base URL
`/api/v1`

---

## 1. Treks API

### Get All Treks
- **URL**: `/api/v1/treks`
- **Method**: `GET`
- **Description**: Retrieves a list of all treks. Supports query parameters for filtering (e.g., `?difficulty=Hard&status=Open`).
- **Response**: `200 OK` with a JSON array of trek objects.

### Get Trek by ID
- **URL**: `/api/v1/treks/<int:trek_id>`
- **Method**: `GET`
- **Description**: Retrieves detailed information about a specific trek.
- **Response**: `200 OK` with trek JSON, or `404 Not Found`.

### Create a New Trek (Admin Only)
- **URL**: `/api/v1/treks`
- **Method**: `POST`
- **Description**: Creates a new trek. Requires Admin authentication.
- **Payload**: JSON with `name`, `location`, `difficulty`, `duration`, `available_slots`, etc.
- **Response**: `201 Created` on success.

### Update a Trek (Admin/Staff)
- **URL**: `/api/v1/treks/<int:trek_id>`
- **Method**: `PUT`
- **Description**: Updates trek details. Staff can only update `available_slots` and `status`.
- **Response**: `200 OK` on success.

### Delete a Trek (Admin Only)
- **URL**: `/api/v1/treks/<int:trek_id>`
- **Method**: `DELETE`
- **Description**: Removes a trek from the system.
- **Response**: `204 No Content` on success.

---

## 2. Users API

### Get All Users (Admin Only)
- **URL**: `/api/v1/users`
- **Method**: `GET`
- **Description**: Retrieves a list of all registered users (Trekkers and Staff).
- **Response**: `200 OK` with JSON array of users.

### Get User Profile
- **URL**: `/api/v1/users/<int:user_id>`
- **Method**: `GET`
- **Description**: Retrieves details for a specific user.
- **Response**: `200 OK` with user details.

### Update User Profile
- **URL**: `/api/v1/users/<int:user_id>`
- **Method**: `PUT`
- **Description**: Update user information (e.g. contact details).
- **Response**: `200 OK` on success.

---

## 3. Bookings API

### Get All Bookings (Admin/Staff)
- **URL**: `/api/v1/bookings`
- **Method**: `GET`
- **Description**: Retrieves all bookings. Staff can filter by `?trek_id=123` to see only bookings for their assigned treks.
- **Response**: `200 OK` with JSON array of bookings.

### Create a Booking (User)
- **URL**: `/api/v1/bookings`
- **Method**: `POST`
- **Description**: Books a specific trek for the authenticated user.
- **Payload**: JSON with `trek_id`.
- **Response**: `201 Created` on success, or `400 Bad Request` if overbooked/duplicate.

### Cancel/Update a Booking
- **URL**: `/api/v1/bookings/<int:booking_id>`
- **Method**: `PUT`
- **Description**: Updates booking status (e.g. 'Cancelled' by User, or 'Completed' by Staff).
- **Payload**: JSON with `status`.
- **Response**: `200 OK` on success.

---

## Authentication for APIs
If using APIs directly, token-based authentication (like JWT) or Flask-Login session cookies will be enforced to ensure secure access.
