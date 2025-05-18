# Notification-Service
A scalable backend system built with FastAPI to send and manage notifications for users. Supports Email, SMS, and in-app notifications. Uses Celery with RabbitMQ for asynchronous task processing and retries on failure.
What it does
1. You can send a notification to a user through an API.
2.You can get a list of notifications sent to a specific user.
3.Uses a task queue (Celery) with RabbitMQ to handle sending notifications in the background.
4.Automatically retries sending notifications if they fail.
5.Stores notification data in a simple SQLite database.
6.The whole system runs in Docker containers for easy setup.
