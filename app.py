from flask_cors import CORS
from flask import Flask, jsonify
from joblib import load
import mysql.connector
import os

app = Flask(__name__)

# Load the trained KNN model
model = load('rf_model.joblib')

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
    cursor.execute(f"SELECT education, currentSmoker, cigsPerDay, BPMeds, prevalentStroke, prevalentHyp, diabetes, BMI, totChol, sysBP, diaBP, heartRate, glucose FROM heart_disease_test WHERE patient_id = {patient_id}")
    heart_data = cursor.fetchone()

    # Check if heart data exists for the patient
    if not heart_data:
        return jsonify({'error': 'Heart data not found for the patient'}), 404

    education, currentSmoker, cigsPerDay, BPMeds, prevalentStroke, prevalentHyp, diabetes, BMI, totChol, sysBP, diaBP, heartRate, glucose = heart_data

    # Close database connection
    cursor.close()
    connection.close()

    features = [
        male, age, education, currentSmoker, cigsPerDay, BPMeds, prevalentStroke, prevalentHyp, diabetes, totChol, sysBP, diaBP, BMI, heartRate, glucose
    ]
    features = [float(f) for f in features]
    prediction = model.predict([features])

    # Convert the prediction to a descriptive message
    if prediction[0] == 0:
        result = "The patient will not develop heart disease."
        prediction_value = 0
    else:
        result = "The patient will develop heart disease."
        prediction_value = 1

    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Add CHD column to heart_disease_test table if it doesn't exist
        cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'heart_disease_test' AND COLUMN_NAME = 'CHD'")
        if not cursor.fetchone():
            # Add CHD column to heart_disease_test table if it doesn't exist
            cursor.execute("ALTER TABLE heart_disease_test ADD COLUMN CHD INT")
            connection.commit()

        # Update the heart_disease_test table with the prediction result in the CHD column
        update_query = f"UPDATE heart_disease_test SET CHD = {prediction_value} WHERE patient_id = {patient_id}"
        cursor.execute(update_query)
        update_count = cursor.rowcount  # Get the number of rows affected
        connection.commit()

        update_status = "Update successful" if update_count > 0 else "No rows updated"
    except mysql.connector.Error as err:
        return jsonify({'error': f'Database error: {err}'}), 500
    finally:
        cursor.close()
        connection.close()

    return jsonify({
        'prediction': result,
        'features': {
            'data': update_status,
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
            'totChol' : totChol,
            'sysBP' : sysBP,
            'diaBP' : diaBP,
            'BMI': BMI,
            'heartRate' : heartRate,
            'glucose' : glucose
        }
    })

    

CORS(app, origins=[
    'http://localhost:3000',
    'https://e-react-frontend-55dbf7a5897e.herokuapp.com'
])


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
