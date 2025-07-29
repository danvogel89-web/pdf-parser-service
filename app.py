from flask import Flask, request, jsonify
import pdfplumber, requests
from io import BytesIO

app = Flask(__name__)

@app.route('/parse', methods=['POST'])
def parse_pdf():
    data = request.get_json()
    file_url = data.get("fileUrl")
    if not file_url:
        return jsonify({"error": "fileUrl missing"}), 400

    # Step 1: Download the PDF
    try:
        resp = requests.get(file_url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] File download failed: {e}", flush=True)
        return jsonify({"error": f"File download failed: {str(e)}"}), 500

    transactions = []

    # Step 2: Parse PDF safely
    try:
        with pdfplumber.open(BytesIO(resp.content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.splitlines():
                    # Keep only lines that likely contain monetary values
                    if any(currency in line for currency in ["£", "€", "$"]):
                        transactions.append({"raw_line": line})

        return jsonify({"transactions": transactions})

    except Exception as e:
        print(f"[ERROR] PDF parsing failed: {e}", flush=True)
        return jsonify({"error": f"PDF parsing failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000) 
