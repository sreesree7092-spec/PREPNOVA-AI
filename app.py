from flask import Flask, render_template, request, session
import os
from werkzeug.utils import secure_filename
from pypdf import PdfReader
from dotenv import load_dotenv
import resend
from html import escape

load_dotenv()

app = Flask(__name__)
app.secret_key = "prepnovai_secret_key"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# EMAIL FINAL RESULT THROUGH RESEND
# =========================================================

def send_result_email():
    """Send the five-round result to the student's submitted email."""
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    recipient = session.get("student_email", "").strip()

    if not api_key:
        print("RESULT EMAIL ERROR: RESEND_API_KEY is missing in .env")
        return False, "Missing Resend API key."

    if not recipient:
        print("RESULT EMAIL ERROR: Student email is missing.")
        return False, "Student email is missing."

    labels = ["Aptitude", "Technical", "HR Voice", "Coding", "Mock Interview"]
    scores = [int(session.get(f"round{i}_score", 0) or 0) for i in range(1, 6)]
    overall = round(sum(scores) / 5)
    rows = "".join(
        "<tr><td style=\"padding:8px;border:1px solid #ddd\">"
        + escape(label)
        + "</td><td style=\"padding:8px;border:1px solid #ddd\">"
        + str(score)
        + "/100</td></tr>"
        for label, score in zip(labels, scores)
    )
    student_name = escape(session.get("student_name", "Student"))
    department = escape(session.get("department", "Not provided"))
    html_content = f"""
    <div style=\"font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#222\">
      <h2 style=\"color:#673ab7\">PREPNOVA AI — Final Assessment Result</h2>
      <p>Hello {student_name},</p>
      <p>Your five-round assessment is complete.</p>
      <p><b>Department:</b> {department}</p>
      <table style=\"border-collapse:collapse;width:100%\">
        <thead><tr><th style=\"padding:8px;border:1px solid #ddd;text-align:left\">Round</th>
        <th style=\"padding:8px;border:1px solid #ddd;text-align:left\">Score</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <h3>Overall score: {overall}%</h3>
      <p>Thank you for using PREPNOVA AI. Keep practising and improving your interview skills.</p>
      <p>Regards,<br><b>PREPNOVA AI</b></p>
    </div>
    """

    try:
        resend.api_key = api_key
        response = resend.Emails.send({
            "from": os.getenv("RESEND_FROM_EMAIL", "PREPNOVA AI <onboarding@resend.dev>"),
            "to": [recipient],
            "subject": "Your PREPNOVA AI Final Assessment Result",
            "html": html_content,
        })
        print("RESULT EMAIL SENT:", response)
        return True, "Result email sent."
    except Exception as exc:
        print("RESULT EMAIL ERROR:", exc)
        return False, str(exc)


# =========================================================
# RESUME SKILLS
# =========================================================

skills_list = [
    "Python",
    "Java",
    "C",
    "C++",
    "HTML",
    "CSS",
    "JavaScript",
    "SQL",
    "Machine Learning",
    "Artificial Intelligence",
    "Data Analytics",
    "Flask",
    "React",
    "Django",
    "MySQL",
    "MongoDB",
    "MATLAB",
    "Embedded C"
]


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# STUDENT LOGIN
# =========================================================

@app.route("/student", methods=["GET", "POST"])
def student():

    if request.method == "POST":

        name = request.form.get("name", "")
        email = request.form.get("email", "")
        department = request.form.get("department", "")

        resume = request.files.get("resume")

        resume_text = ""
        found_skills = []

        # -------------------------------------------------
        # RESUME
        # -------------------------------------------------

        if resume and resume.filename != "":

            filename = secure_filename(resume.filename)

            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            resume.save(file_path)

            try:

                reader = PdfReader(file_path)

                for page in reader.pages:

                    text = page.extract_text()

                    if text:
                        resume_text += text + "\n"

            except Exception as e:

                print("PDF ERROR:", e)

            resume_lower = resume_text.lower()

            for skill in skills_list:

                if skill.lower() in resume_lower:

                    found_skills.append(skill)

        # -------------------------------------------------
        # STUDENT SESSION
        # -------------------------------------------------

        session["student_name"] = name
        session["student_email"] = email
        session["department"] = department
        session["resume_text"] = resume_text
        session["skills"] = found_skills

        # -------------------------------------------------
        # RESET COMPLETION
        # -------------------------------------------------

        for round_number in range(1, 6):

            session[f"round{round_number}_completed"] = False
            session[f"round{round_number}_score"] = 0

        return render_template(
            "rounds.html",
            name=name,
            department=department,
            skills=found_skills
        )

    return render_template("student.html")


# =========================================================
# ROUND 1
# =========================================================

@app.route("/round1")
def round1():

    if "student_name" not in session:

        return "Please login first."

    return render_template("round1.html")


@app.route("/round1-complete", methods=["POST"])
def round1_complete():

    data = request.get_json(silent=True) or {}

    score = data.get("score", 0)

    try:
        score = float(score)
    except:
        score = 0

    score = max(0, min(100, score))

    session["round1_score"] = round(score)
    session["round1_completed"] = True

    print("ROUND 1 SCORE:", score)

    return {
        "success": True,
        "score": round(score)
    }


# =========================================================
# ROUND 2
# =========================================================

@app.route("/round2")
def round2():

    if "student_name" not in session:

        return "Please login first."

    if not session.get("round1_completed", False):

        return """
        <h2>🔒 Round 2 Locked</h2>
        <p>Please complete Round 1 first.</p>
        """

    return render_template(
        "round2.html",
        name=session.get("student_name", ""),
        department=session.get("department", ""),
        skills=session.get("skills", [])
    )


@app.route("/round2-complete", methods=["POST"])
def round2_complete():

    data = request.get_json(silent=True) or {}

    score = data.get("score", 0)

    try:
        score = float(score)
    except:
        score = 0

    score = max(0, min(100, score))

    session["round2_score"] = round(score)
    session["round2_completed"] = True

    print("ROUND 2 SCORE:", score)

    return {
        "success": True,
        "score": round(score)
    }


# =========================================================
# ROUND 3
# =========================================================

@app.route("/round3")
def round3():

    if "student_name" not in session:

        return "Please login first."

    if not session.get("round2_completed", False):

        return """
        <h2>🔒 Round 3 Locked</h2>
        <p>Please complete Round 2 first.</p>
        """

    return render_template(
        "round3.html",
        name=session.get("student_name", ""),
        department=session.get("department", ""),
        skills=session.get("skills", [])
    )


@app.route("/round3-complete", methods=["POST"])
def round3_complete():

    data = request.get_json(silent=True) or {}

    score = data.get("score", 0)

    try:
        score = float(score)
    except:
        score = 0

    score = max(0, min(100, score))

    session["round3_score"] = round(score)
    session["round3_completed"] = True

    print("ROUND 3 SCORE:", score)

    return {
        "success": True,
        "score": round(score)
    }


# =========================================================
# ROUND 4
# =========================================================

@app.route("/round4")
def round4():

    if "student_name" not in session:

        return "Please login first."

    if not session.get("round3_completed", False):

        return """
        <h2>🔒 Round 4 Locked</h2>
        <p>Please complete Round 3 first.</p>
        """

    return render_template(
        "round4.html",
        name=session.get("student_name", ""),
        department=session.get("department", "")
    )


@app.route("/round4-complete", methods=["POST"])
def round4_complete():

    data = request.get_json(silent=True) or {}

    score = data.get("score", 0)

    try:
        score = float(score)
    except:
        score = 0

    score = max(0, min(100, score))

    session["round4_score"] = round(score)
    session["round4_completed"] = True

    print("ROUND 4 SCORE:", score)

    return {
        "success": True,
        "score": round(score)
    }


# =========================================================
# ROUND 5
# =========================================================

@app.route("/round5")
def round5():

    if "student_name" not in session:

        return "Please login first."

    if not session.get("round4_completed", False):

        return """
        <h2>🔒 Round 5 Locked</h2>
        <p>Please complete Round 4 first.</p>
        """

    return render_template(
        "round5.html",
        name=session.get("student_name", ""),
        department=session.get("department", ""),
        skills=session.get("skills", [])
    )


@app.route("/round5-complete", methods=["POST"])
def round5_complete():

    data = request.get_json(silent=True) or {}

    score = data.get("score", 0)

    try:
        score = float(score)
    except:
        score = 0

    score = max(0, min(100, score))

    session["round5_score"] = round(score)
    session["round5_completed"] = True

    print("ROUND 5 SCORE:", score)

    # Send final result email after Round 5 is completed.
    email_sent, email_message = send_result_email()

    return {
        "success": True,
        "score": round(score),
        "email_sent": email_sent,
        "email_message": email_message
    }


# =========================================================
# ROUNDS PAGE
# =========================================================

@app.route("/rounds")
def rounds():

    if "student_name" not in session:

        return "Please login first."

    return render_template(
        "rounds.html",
        name=session.get("student_name", ""),
        department=session.get("department", ""),
        skills=session.get("skills", [])
    )


# =========================================================
# FINAL RESULT
# =========================================================

@app.route("/result")
def result():

    if "student_name" not in session:

        return "Please login first."

    # -----------------------------------------------------
    # GET SCORES
    # -----------------------------------------------------

    round1 = session.get("round1_score", 0)
    round2 = session.get("round2_score", 0)
    round3 = session.get("round3_score", 0)
    round4 = session.get("round4_score", 0)
    round5 = session.get("round5_score", 0)

    scores = [
        round1,
        round2,
        round3,
        round4,
        round5
    ]

    # -----------------------------------------------------
    # OVERALL
    # -----------------------------------------------------

    overall = round(
        sum(scores) / len(scores)
    )

    # -----------------------------------------------------
    # CAREER READINESS
    # -----------------------------------------------------

    if overall >= 85:

        readiness = "Excellent"
        readiness_icon = "🌟"

    elif overall >= 70:

        readiness = "Good"
        readiness_icon = "🎯"

    elif overall >= 50:

        readiness = "Developing"
        readiness_icon = "📈"

    else:

        readiness = "Needs Improvement"
        readiness_icon = "💪"

    # -----------------------------------------------------
    # ROUND INFORMATION
    # -----------------------------------------------------

    round_data = [

        {
            "name": "Round 1",
            "title": "Aptitude",
            "score": round1
        },

        {
            "name": "Round 2",
            "title": "Technical",
            "score": round2
        },

        {
            "name": "Round 3",
            "title": "HR Voice",
            "score": round3
        },

        {
            "name": "Round 4",
            "title": "Coding",
            "score": round4
        },

        {
            "name": "Round 5",
            "title": "Mock Interview",
            "score": round5
        }

    ]

    # -----------------------------------------------------
    # STRONG AREAS
    # -----------------------------------------------------

    strong_areas = []

    for item in round_data:

        if item["score"] >= 75:

            strong_areas.append(
                item["title"]
            )

    # -----------------------------------------------------
    # WEAK AREAS
    # -----------------------------------------------------

    weak_areas = []

    for item in round_data:

        if item["score"] < 60:

            weak_areas.append(
                item["title"]
            )

    # -----------------------------------------------------
    # RECOMMENDATIONS
    # -----------------------------------------------------

    recommendations = []

    if round1 < 60:

        recommendations.append(
            "🎯 Practice aptitude topics such as percentages, "
            "logical reasoning, time & work and quantitative problems."
        )

    if round2 < 60:

        recommendations.append(
            "💻 Strengthen your department-related technical "
            "concepts and resume-based interview questions."
        )

    if round3 < 60:

        recommendations.append(
            "🗣️ Practice speaking clearly and answering HR "
            "questions using structured examples."
        )

    if round4 < 60:

        recommendations.append(
            "🧠 Practice programming problems, algorithms, "
            "arrays, strings and problem-solving."
        )

    if round5 < 60:

        recommendations.append(
            "🎤 Practice explaining your projects, strengths, "
            "career goals and technical skills confidently."
        )

    if not recommendations:

        recommendations.append(
            "🚀 Keep practising regularly and continue improving "
            "your technical and interview skills."
        )

    # -----------------------------------------------------
    # PERFORMANCE
    # -----------------------------------------------------

    performance = [

        {
            "name": "Aptitude",
            "score": round1
        },

        {
            "name": "Technical Knowledge",
            "score": round2
        },

        {
            "name": "Communication",
            "score": round3
        },

        {
            "name": "Problem Solving",
            "score": round4
        },

        {
            "name": "Interview Confidence",
            "score": round5
        }

    ]

    return render_template(
        "result.html",

        name=session.get("student_name", ""),

        department=session.get("department", ""),

        skills=session.get("skills", []),

        round_data=round_data,

        performance=performance,

        overall=overall,

        readiness=readiness,

        readiness_icon=readiness_icon,

        strong_areas=strong_areas,

        weak_areas=weak_areas,

        recommendations=recommendations

    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )