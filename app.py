from flask_cors import CORS
from flask import Flask, jsonify
from joblib import load
import mysql.connector
import os

app = Flask(__name__)

# Load the trained KNN model
model = load('lg_model.joblib')

# Set up MySQL connection parameters
db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

@app.route('/predict/phone/<phone_number>', methods=['GET'])
def predict_by_phone(phone_number):
    # Connect to the MySQL database
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    # Fetch data from patient_registration table based on phone number
    cursor.execute(f"SELECT id, Age, Gender FROM patients_registration WHERE MobileNumber = '{phone_number}'")
    patient_data = cursor.fetchone()

    # Check if patient data exists
    if not patient_data:
        return jsonify({'error': 'Patient not found'}), 404

    patient_id, age, gender = patient_data
    male = 1 if gender == 'Male' else 0

    # Fetch data from heart_disease_test table
    cursor.execute(f"SELECT education, currentSmoker, cigsPerDay, BPMeds, prevalentStroke, prevalentHyp, diabetes, BMI FROM heart_disease_test WHERE patient_id = {patient_id}")
    heart_data = cursor.fetchone()

    # Check if heart data exists for the patient
    if not heart_data:
        return jsonify({'error': 'Heart data not found for the patient'}), 404

    education, currentSmoker, cigsPerDay, BPMeds, prevalentStroke, prevalentHyp, diabetes, BMI = heart_data

    # Close database connection
    cursor.close()
    connection.close()

    features = [
        male, age, education, currentSmoker, cigsPerDay, BPMeds, prevalentStroke, prevalentHyp, diabetes, BMI
    ]
    features = [float(f) for f in features]
    prediction = model.predict([features])

    # Convert the prediction to a descriptive message
    if prediction[0] == 0:
        result = "The patient will not develop heart disease."
    else:
        result = "The patient will develop heart disease."

    return jsonify({
        'prediction': result,
        'features': {
            'id': patient_id,
            'male': male,
            'age': age,
            'education': education,
            'currentSmoker': currentSmoker,
            'cigsPerDay': cigsPerDay,
            'BPMeds': BPMeds,
            'prevalentStroke': prevalentStroke,
            'prevalentHyp': prevalentHyp,
            'diabetes': diabetes,
            'BMI': BMI

        }
    })

CORS(app, origins=['http://localhost:3000'])

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
