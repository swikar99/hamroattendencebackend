#!/bin/bash

echo "========================================="
echo "Attendance Management System - Setup"
echo "========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate

echo "Creating superuser..."
echo "Please enter superuser credentials:"
python manage.py createsuperuser

echo "Loading initial data..."
python init_data.py

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "To start the development server:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "Access the application at:"
echo "  API: http://localhost:8000/api/"
echo "  Admin: http://localhost:8000/admin/"
echo ""
