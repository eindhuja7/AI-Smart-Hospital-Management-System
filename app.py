from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from dotenv import load_dotenv
import os

# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "smart_hospital_secret_key"
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.getenv("MYSQL_PASSWORD"),
        database="hospital_management"
    )


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required():

    if "user_id" not in session:
        return False

    return True


# =========================================================
# NOTIFICATIONS
# =========================================================

def get_notifications():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    notifications = []

    # -----------------------------------------------------
    # TODAY'S APPOINTMENTS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM appointments
        WHERE appointment_date = CURDATE()
        """
    )

    today_appointments = cursor.fetchone()["total"]

    if today_appointments > 0:

        notifications.append({
            "type": "success",
            "icon": "📅",
            "message":
                f"You have {today_appointments} appointment(s) scheduled for today."
        })

    else:

        notifications.append({
            "type": "info",
            "icon": "📅",
            "message":
                "No appointments are scheduled for today."
        })

    # -----------------------------------------------------
    # AVAILABLE DOCTORS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM doctors
        WHERE available_time IS NOT NULL
        AND available_time != ''
        """
    )

    available_doctors = cursor.fetchone()["total"]

    if available_doctors > 3:

        notifications.append({
            "type": "success",
            "icon": "👨‍⚕️",
            "message":
                f"{available_doctors} doctors are currently available."
        })

    else:

        notifications.append({
            "type": "warning",
            "icon": "⚠️",
            "message":
                "Warning: Very few doctors are currently available."
        })

    # -----------------------------------------------------
    # LATEST PATIENT
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT name
        FROM patients
        ORDER BY patient_id DESC
        LIMIT 1
        """
    )

    recent_patient = cursor.fetchone()

    if recent_patient:

        notifications.append({
            "type": "patient",
            "icon": "👤",
            "message":
                f"Latest patient registered: {recent_patient['name']}"
        })

    # -----------------------------------------------------
    # LATEST DOCTOR
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT name
        FROM doctors
        ORDER BY doctor_id DESC
        LIMIT 1
        """
    )

    recent_doctor = cursor.fetchone()

    if recent_doctor:

        notifications.append({
            "type": "doctor",
            "icon": "👨‍⚕️",
            "message":
                f"Latest doctor registered: Dr. {recent_doctor['name']}"
        })

    # -----------------------------------------------------
    # PENDING LAB TESTS
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM lab_tests
        WHERE status = 'Pending'
        """
    )

    pending_tests = cursor.fetchone()["total"]

    if pending_tests > 0:

        notifications.append({
            "type": "warning",
            "icon": "🧪",
            "message":
                f"{pending_tests} lab test(s) are still pending."
        })

    cursor.close()
    db.close()

    return notifications


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username = %s
            AND password = %s
            """,
            (username, password)
        )

        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user:

            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(
                url_for("home")
            )

        return render_template(
            "login.html",
            error="Invalid username or password"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# HOME / DASHBOARD
# =========================================================

@app.route("/")
def home():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # TOTAL PATIENTS

    cursor.execute(
        "SELECT COUNT(*) AS total FROM patients"
    )

    total_patients = cursor.fetchone()["total"]

    # TOTAL DOCTORS

    cursor.execute(
        "SELECT COUNT(*) AS total FROM doctors"
    )

    total_doctors = cursor.fetchone()["total"]

    # TODAY'S APPOINTMENTS

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM appointments
        WHERE appointment_date = CURDATE()
        """
    )

    today_appointments = cursor.fetchone()["total"]

    # AVAILABLE DOCTORS

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM doctors
        WHERE available_time IS NOT NULL
        AND available_time != ''
        """
    )

    available_doctors = cursor.fetchone()["total"]

    cursor.close()
    db.close()

    notifications = get_notifications()

    return render_template(
        "index.html",
        total_patients=total_patients,
        total_doctors=total_doctors,
        today_appointments=today_appointments,
        available_doctors=available_doctors,
        notifications=notifications,
        username=session.get("username"),
        role=session.get("role")
    )


# =========================================================
# NOTIFICATIONS PAGE
# =========================================================

@app.route("/notifications")
def notifications_page():

    if not login_required():

        return redirect(
            url_for("login")
        )

    notifications = get_notifications()

    return render_template(
        "notifications.html",
        notifications=notifications
    )


# =========================================================
# MARK NOTIFICATIONS AS READ
# =========================================================

@app.route("/notifications/read")
def notifications_read():

    if not login_required():

        return redirect(
            url_for("login")
        )

    return redirect(
        url_for("home")
    )


# =========================================================
# PATIENT REGISTRATION
# =========================================================

@app.route("/patient", methods=["GET", "POST"])
def patient():

    if not login_required():

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        phone = request.form["phone"]
        email = request.form.get("email", "")
        address = request.form["address"]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO patients
            (
                name,
                age,
                gender,
                phone,
                email,
                address
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                age,
                gender,
                phone,
                email,
                address
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("patient_success")
        )

    return render_template(
        "patient_registration.html"
    )


# =========================================================
# PATIENT SUCCESS
# =========================================================

@app.route("/patient-success")
def patient_success():

    if not login_required():

        return redirect(
            url_for("login")
        )

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>Patient Registration Success</title>

    </head>

    <body style="
        font-family: Arial;
        text-align: center;
        padding-top: 100px;
        background: #f4f7fb;
    ">

        <div style="
            background: white;
            max-width: 550px;
            margin: auto;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.10);
        ">

            <div style="font-size: 60px;">
                ✅
            </div>

            <h1 style="color: green;">
                Patient Registered Successfully!
            </h1>

            <p>
                Patient details have been saved
                successfully.
            </p>

            <br>

            <a href="/patient"
               style="
                    text-decoration:none;
                    background:#2563eb;
                    color:white;
                    padding:12px 20px;
                    border-radius:10px;
                    font-weight:bold;
               ">

                ➕ Register Another Patient

            </a>

            <br><br><br>

            <a href="/patients"
               style="
                    text-decoration:none;
                    color:#2563eb;
                    font-weight:bold;
               ">

                👥 View Patients

            </a>

            <br><br>

            <a href="/"
               style="
                    text-decoration:none;
                    color:#2563eb;
                    font-weight:bold;
               ">

                🏠 Back to Dashboard

            </a>

        </div>

    </body>

    </html>
    """


# =========================================================
# VIEW PATIENTS
# =========================================================

@app.route("/patients")
def patients():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM patients
        ORDER BY patient_id DESC
        """
    )

    patient_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "patients.html",
        patients=patient_list
    )


# =========================================================
# DELETE PATIENT
# =========================================================

@app.route(
    "/delete-patient/<int:patient_id>",
    methods=["POST"]
)
def delete_patient(patient_id):

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor()

    try:

        # CHECK APPOINTMENTS

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM appointments
            WHERE patient_id = %s
            """,
            (patient_id,)
        )

        appointment_count = cursor.fetchone()[0]

        # CHECK MEDICAL HISTORY

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM medical_history
            WHERE patient_id = %s
            """,
            (patient_id,)
        )

        history_count = cursor.fetchone()[0]

        # CHECK PRESCRIPTIONS

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM prescriptions
            WHERE patient_id = %s
            """,
            (patient_id,)
        )

        prescription_count = cursor.fetchone()[0]

        # CHECK LAB TESTS

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM lab_tests
            WHERE patient_id = %s
            """,
            (patient_id,)
        )

        lab_count = cursor.fetchone()[0]

        # IF RELATED RECORDS EXIST

        if (
            appointment_count > 0
            or history_count > 0
            or prescription_count > 0
            or lab_count > 0
        ):

            print(
                "Patient cannot be deleted because related records exist."
            )

            db.rollback()

        else:

            cursor.execute(
                """
                DELETE FROM patients
                WHERE patient_id = %s
                """,
                (patient_id,)
            )

            db.commit()

    except mysql.connector.Error as e:

        db.rollback()

        print(
            "Delete Error:",
            e
        )

    cursor.close()
    db.close()

    return redirect(
        url_for("patients")
    )


# =========================================================
# DOCTOR REGISTRATION
# =========================================================

@app.route("/doctor", methods=["GET", "POST"])
def doctor():

    if not login_required():

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        name = request.form["name"]

        specialization = request.form[
            "specialization"
        ]

        phone = request.form["phone"]

        email = request.form.get(
            "email",
            ""
        )

        available_time = request.form[
            "available_time"
        ]

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO doctors
            (
                name,
                specialization,
                phone,
                email,
                available_time
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                name,
                specialization,
                phone,
                email,
                available_time
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("doctor_success")
        )

    return render_template(
        "doctor_registration.html"
    )


# =========================================================
# DOCTOR SUCCESS
# =========================================================

@app.route("/doctor-success")
def doctor_success():

    if not login_required():

        return redirect(
            url_for("login")
        )

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>Doctor Registration Success</title>

    </head>

    <body style="
        font-family: Arial;
        text-align: center;
        padding-top: 100px;
        background: #f4f7fb;
    ">

        <div style="
            background: white;
            max-width: 550px;
            margin: auto;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.10);
        ">

            <div style="font-size:60px;">
                ✅
            </div>

            <h1 style="color:green;">
                Doctor Registered Successfully!
            </h1>

            <p>
                Doctor details have been saved
                successfully.
            </p>

            <br>

            <a href="/doctor"
               style="
                    text-decoration:none;
                    background:#2563eb;
                    color:white;
                    padding:12px 20px;
                    border-radius:10px;
                    font-weight:bold;
               ">

                ➕ Register Another Doctor

            </a>

            <br><br><br>

            <a href="/doctors"
               style="
                    text-decoration:none;
                    color:#2563eb;
                    font-weight:bold;
               ">

                👨‍⚕️ View Doctors

            </a>

            <br><br>

            <a href="/"
               style="
                    text-decoration:none;
                    color:#2563eb;
                    font-weight:bold;
               ">

                🏠 Back to Dashboard

            </a>

        </div>

    </body>

    </html>
    """


# =========================================================
# VIEW DOCTORS
# =========================================================

@app.route("/doctors")
def doctors():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT *
        FROM doctors
        ORDER BY doctor_id DESC
        """
    )

    doctor_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "doctors.html",
        doctors=doctor_list
    )


# =========================================================
# BOOK APPOINTMENT
# =========================================================

@app.route(
    "/appointment",
    methods=["GET", "POST"]
)
def appointment():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # PATIENT LIST

    cursor.execute(
        """
        SELECT patient_id, name
        FROM patients
        ORDER BY name
        """
    )

    patient_list = cursor.fetchall()

    # DOCTOR LIST

    cursor.execute(
        """
        SELECT
            doctor_id,
            name,
            specialization
        FROM doctors
        ORDER BY name
        """
    )

    doctor_list = cursor.fetchall()

    # SAVE APPOINTMENT

    if request.method == "POST":

        patient_id = request.form[
            "patient_id"
        ]

        doctor_id = request.form[
            "doctor_id"
        ]

        appointment_date = request.form[
            "appointment_date"
        ]

        appointment_time = request.form[
            "appointment_time"
        ]

        reason = request.form[
            "reason"
        ]

        cursor.execute(
            """
            INSERT INTO appointments
            (
                patient_id,
                doctor_id,
                appointment_date,
                appointment_time,
                reason
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                patient_id,
                doctor_id,
                appointment_date,
                appointment_time,
                reason
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("appointment_success")
        )

    cursor.close()
    db.close()

    return render_template(
        "appointment.html",
        patients=patient_list,
        doctors=doctor_list
    )


# =========================================================
# APPOINTMENT SUCCESS
# =========================================================

@app.route("/appointment-success")
def appointment_success():

    if not login_required():

        return redirect(
            url_for("login")
        )

    return """
    <!DOCTYPE html>

    <html>

    <head>

        <title>Appointment Success</title>

    </head>

    <body style="
        font-family: Arial;
        text-align: center;
        padding-top: 100px;
        background:#f4f7fb;
    ">

        <div style="
            background:white;
            max-width:550px;
            margin:auto;
            padding:40px;
            border-radius:20px;
            box-shadow:0 8px 30px rgba(0,0,0,0.10);
        ">

            <div style="font-size:60px;">
                📅
            </div>

            <h1 style="color:green;">
                Appointment Booked Successfully!
            </h1>

            <p>
                Appointment details have been
                saved successfully.
            </p>

            <br>

            <a href="/appointment"
               style="
                    text-decoration:none;
                    background:#2563eb;
                    color:white;
                    padding:12px 20px;
                    border-radius:10px;
                    font-weight:bold;
               ">

                📅 Book Another Appointment

            </a>

            <br><br><br>

            <a href="/appointments"
               style="
                    text-decoration:none;
                    color:#2563eb;
                    font-weight:bold;
               ">

                📋 View Appointments

            </a>

            <br><br>

            <a href="/"
               style="
                    text-decoration:none;
                    color:#2563eb;
                    font-weight:bold;
               ">

                🏠 Back to Dashboard

            </a>

        </div>

    </body>

    </html>
    """


# =========================================================
# VIEW APPOINTMENTS
# =========================================================

@app.route("/appointments")
def appointments():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT
            appointments.appointment_id,
            appointments.patient_id,
            appointments.doctor_id,
            patients.name AS patient_name,
            doctors.name AS doctor_name,
            doctors.specialization,
            appointments.appointment_date,
            appointments.appointment_time,
            appointments.reason,
            appointments.status

        FROM appointments

        JOIN patients
            ON appointments.patient_id =
               patients.patient_id

        JOIN doctors
            ON appointments.doctor_id =
               doctors.doctor_id

        ORDER BY appointments.appointment_id DESC
        """
    )

    appointment_list = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "appointments.html",
        appointments=appointment_list
    )


# =========================================================
# MEDICAL HISTORY
# =========================================================

@app.route(
    "/medical-history",
    methods=["GET", "POST"]
)
def medical_history():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT patient_id, name
        FROM patients
        ORDER BY name
        """
    )

    patient_list = cursor.fetchall()

    if request.method == "POST":

        patient_id = request.form[
            "patient_id"
        ]

        diagnosis = request.form[
            "diagnosis"
        ]

        treatment = request.form.get(
            "treatment",
            ""
        )

        visit_date = request.form[
            "visit_date"
        ]

        notes = request.form.get(
            "notes",
            ""
        )

        cursor.execute(
            """
            INSERT INTO medical_history
            (
                patient_id,
                diagnosis,
                treatment,
                visit_date,
                notes
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                patient_id,
                diagnosis,
                treatment,
                visit_date,
                notes
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("medical_history")
        )

    cursor.close()
    db.close()

    return render_template(
        "medical_history.html",
        patients=patient_list
    )


# =========================================================
# PRESCRIPTION
# =========================================================

@app.route(
    "/prescription",
    methods=["GET", "POST"]
)
def prescription():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # PATIENTS

    cursor.execute(
        """
        SELECT patient_id, name
        FROM patients
        ORDER BY name
        """
    )

    patient_list = cursor.fetchall()

    # DOCTORS

    cursor.execute(
        """
        SELECT
            doctor_id,
            name,
            specialization
        FROM doctors
        ORDER BY name
        """
    )

    doctor_list = cursor.fetchall()

    # SAVE PRESCRIPTION

    if request.method == "POST":

        patient_id = request.form[
            "patient_id"
        ]

        doctor_id = request.form[
            "doctor_id"
        ]

        medicine = request.form[
            "medicine"
        ]

        dosage = request.form[
            "dosage"
        ]

        duration = request.form[
            "duration"
        ]

        prescription_date = request.form[
            "prescription_date"
        ]

        cursor.execute(
            """
            INSERT INTO prescriptions
            (
                patient_id,
                doctor_id,
                medicine,
                dosage,
                duration,
                prescription_date
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                patient_id,
                doctor_id,
                medicine,
                dosage,
                duration,
                prescription_date
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("prescription")
        )

    cursor.close()
    db.close()

    return render_template(
        "prescription.html",
        patients=patient_list,
        doctors=doctor_list
    )


# =========================================================
# LAB TESTS
# =========================================================

@app.route(
    "/lab-tests",
    methods=["GET", "POST"]
)
def lab_tests():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # PATIENTS

    cursor.execute(
        """
        SELECT patient_id, name
        FROM patients
        ORDER BY name
        """
    )

    patient_list = cursor.fetchall()

    # SAVE LAB TEST

    if request.method == "POST":

        patient_id = request.form[
            "patient_id"
        ]

        test_name = request.form[
            "test_name"
        ]

        test_date = request.form[
            "test_date"
        ]

        result = request.form.get(
            "result",
            ""
        )

        status = request.form[
            "status"
        ]

        cursor.execute(
            """
            INSERT INTO lab_tests
            (
                patient_id,
                test_name,
                test_date,
                result,
                status
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                patient_id,
                test_name,
                test_date,
                result,
                status
            )
        )

        db.commit()

        cursor.close()
        db.close()

        return redirect(
            url_for("lab_tests")
        )

    cursor.close()
    db.close()

    return render_template(
        "lab_tests.html",
        patients=patient_list
    )


# =========================================================
# VIEW LAB TESTS
# =========================================================

@app.route("/lab-test-list")
def lab_test_list():

    if not login_required():

        return redirect(
            url_for("login")
        )

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT

            lab_tests.test_id,

            lab_tests.patient_id,

            patients.name AS patient_name,

            lab_tests.test_name,

            lab_tests.test_date,

            lab_tests.result,

            lab_tests.status

        FROM lab_tests

        JOIN patients
            ON lab_tests.patient_id =
               patients.patient_id

        ORDER BY lab_tests.test_id DESC
        """
    )

    tests = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "lab_test_list.html",
        tests=tests
    )


# =========================================================
# AI HEALTH PREDICTION
# =========================================================

@app.route(
    "/ai-prediction",
    methods=["GET", "POST"]
)
def ai_prediction():

    if not login_required():

        return redirect(
            url_for("login")
        )

    prediction = None
    selected_patient = None

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # PATIENT LIST

    cursor.execute(
        """
        SELECT patient_id, name
        FROM patients
        ORDER BY name
        """
    )

    patient_list = cursor.fetchall()

    # PREDICTION

    if request.method == "POST":

        symptoms = request.form[
            "symptoms"
        ].lower()

        patient_id = request.form.get(
            "patient_id",
            ""
        )

        # SELECTED PATIENT

        if patient_id:

            cursor.execute(
                """
                SELECT name
                FROM patients
                WHERE patient_id = %s
                """,
                (patient_id,)
            )

            patient_data = cursor.fetchone()

            if patient_data:

                selected_patient = patient_data[
                    "name"
                ]

        # BASIC PREDICTION LOGIC

        if (
            "fever" in symptoms
            and
            "cough" in symptoms
        ):

            prediction = (
                "Flu / Viral Infection"
            )

        elif "fever" in symptoms:

            prediction = (
                "Possible Fever / Infection"
            )

        elif "cough" in symptoms:

            prediction = (
                "Possible Respiratory Infection"
            )

        elif "headache" in symptoms:

            prediction = (
                "Possible Headache / Migraine"
            )

        elif "stomach pain" in symptoms:

            prediction = (
                "Possible Gastric Problem"
            )

        elif "cold" in symptoms:

            prediction = (
                "Possible Common Cold"
            )

        elif "sore throat" in symptoms:

            prediction = (
                "Possible Throat Infection"
            )

        else:

            prediction = (
                "No matching condition found"
            )

    cursor.close()
    db.close()

    return render_template(

        "ai_prediction.html",

        prediction=prediction,

        patients=patient_list,

        selected_patient=selected_patient

    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )